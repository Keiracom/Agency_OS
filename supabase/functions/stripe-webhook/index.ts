/**
 * FILE: supabase/functions/stripe-webhook/index.ts
 * PURPOSE: Handle Stripe webhooks to increment founding spots counter
 * TRIGGERS: Stripe checkout.session.completed events
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import Stripe from 'https://esm.sh/stripe@12.0.0'

const stripe = new Stripe(Deno.env.get('STRIPE_SECRET_KEY')!, {
  apiVersion: '2023-10-16',
})

const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

// Founding tier price IDs from Stripe
// These should be set in your Edge Function secrets
const FOUNDING_PRICE_IDS = [
  Deno.env.get('STRIPE_FOUNDING_IGNITION_PRICE_ID'),
  Deno.env.get('STRIPE_FOUNDING_VELOCITY_PRICE_ID'),
  Deno.env.get('STRIPE_FOUNDING_DOMINANCE_PRICE_ID'),
].filter(Boolean) as string[]

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, stripe-signature',
}

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  const signature = req.headers.get('stripe-signature')

  if (!signature) {
    console.error('No stripe-signature header found')
    return new Response('No signature', { status: 400, headers: corsHeaders })
  }

  const body = await req.text()

  let event: Stripe.Event

  try {
    event = stripe.webhooks.constructEvent(
      body,
      signature,
      Deno.env.get('STRIPE_WEBHOOK_SECRET')!
    )
  } catch (err) {
    console.error('Webhook signature verification failed:', (err as Error).message)
    return new Response(`Webhook Error: ${(err as Error).message}`, {
      status: 400,
      headers: corsHeaders
    })
  }

  console.log(`Received Stripe event: ${event.type}`)

  // Handle checkout completion
  if (event.type === 'checkout.session.completed') {
    const session = event.data.object as Stripe.Checkout.Session

    console.log(`Checkout session completed: ${session.id}`)

    try {
      // Get line items to check if this is a founding tier subscription
      const lineItems = await stripe.checkout.sessions.listLineItems(session.id)

      const isFoundingTier = lineItems.data.some(item =>
        item.price?.id && FOUNDING_PRICE_IDS.includes(item.price.id)
      )

      if (isFoundingTier) {
        console.log('Founding tier subscription detected!')

        const supabase = createClient(supabaseUrl, supabaseServiceKey)

        // Check if spots are still available
        const { data: available } = await supabase.rpc('founding_spots_available')

        if (!available) {
          console.warn('No founding spots available - subscription was processed but counter not incremented')
          // You might want to handle this case - perhaps notify admin or refund
          return new Response(JSON.stringify({
            received: true,
            warning: 'No founding spots available'
          }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          })
        }

        // Increment founding spots counter
        const { error } = await supabase.rpc('increment_founding_spots')

        if (error) {
          console.error('Error incrementing founding spots:', error)
          return new Response(JSON.stringify({
            received: true,
            error: 'Failed to increment founding spots'
          }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          })
        }

        console.log('Founding spot claimed successfully!')

        // Get remaining spots for logging
        const { data: remaining } = await supabase.rpc('get_remaining_founding_spots')
        console.log(`Remaining founding spots: ${remaining}`)

        // If no spots remaining, log warning (admin should disable founding prices)
        if (remaining !== null && remaining <= 0) {
          console.warn('*** ALL FOUNDING SPOTS CLAIMED! ***')
          console.warn('Consider disabling founding prices in Stripe Dashboard')
          // Optional: You could automate disabling the prices here
          // or send a notification to admin
        }

        // Optional: Store which customer got a founding spot
        if (session.customer) {
          const { error: logError } = await supabase
            .from('activities')
            .insert({
              type: 'founding_spot_claimed',
              metadata: {
                stripe_customer_id: session.customer,
                stripe_session_id: session.id,
                price_id: lineItems.data[0]?.price?.id,
                remaining_spots: remaining
              }
            })

          if (logError) {
            console.warn('Could not log founding spot claim:', logError)
          }
        }
      } else {
        console.log('Regular (non-founding) subscription - no action needed')
      }
    } catch (err) {
      console.error('Error processing checkout:', err)
      // Don't return error - Stripe will retry if we return non-200
      // and we don't want duplicate spot increments
    }
  }

  // Handle subscription cancellation (optional: decrement spots)
  if (event.type === 'customer.subscription.deleted') {
    const subscription = event.data.object as Stripe.Subscription

    // Check if this was a founding subscription
    const isFoundingSubscription = subscription.items.data.some(item =>
      item.price?.id && FOUNDING_PRICE_IDS.includes(item.price.id)
    )

    if (isFoundingSubscription) {
      console.log('Founding subscription cancelled')
      // Note: We don't decrement spots on cancellation
      // Once a spot is taken, it stays taken (per business rules)
      // If you want to release spots on cancellation, add that logic here
    }
  }

  return new Response(JSON.stringify({ received: true }), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  })
})
