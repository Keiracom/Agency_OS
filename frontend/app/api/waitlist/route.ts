/**
 * FILE: app/api/waitlist/route.ts
 * PURPOSE: Waitlist signup API endpoint - stores in Supabase + sends via Resend
 */

import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

// Supabase client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

// Resend API for email
const RESEND_API_KEY = process.env.RESEND_API_KEY;
const RESEND_AUDIENCE_ID = process.env.RESEND_AUDIENCE_ID;

interface WaitlistRequest {
  email: string;
  agencyName?: string;
  source?: string;
}

export async function POST(request: NextRequest) {
  try {
    const body: WaitlistRequest = await request.json();
    const { email, agencyName, source = "landing-page" } = body;

    // Validate email
    if (!email || !email.includes("@")) {
      return NextResponse.json(
        { error: "Valid email is required" },
        { status: 400 }
      );
    }

    // Store in Supabase (if configured)
    if (supabaseUrl && supabaseServiceKey) {
      try {
        const supabase = createClient(supabaseUrl, supabaseServiceKey);
        
        // Check if email already exists
        const { data: existing } = await supabase
          .from("waitlist")
          .select("id")
          .eq("email", email.toLowerCase())
          .single();

        if (existing) {
          return NextResponse.json({
            success: true,
            message: "You're already on the waitlist!",
            alreadyExists: true,
          });
        }

        // Insert new waitlist entry
        const { error: insertError } = await supabase
          .from("waitlist")
          .insert({
            email: email.toLowerCase(),
            agency_name: agencyName || null,
            source,
            status: "pending",
            created_at: new Date().toISOString(),
          });

        if (insertError) {
          console.error("Supabase insert error:", insertError);
          // Continue anyway - we'll still send the email
        }
      } catch (dbError) {
        console.error("Database error:", dbError);
        // Continue anyway - we'll still try to send the email
      }
    }

    // Send via Resend (if configured)
    if (RESEND_API_KEY) {
      try {
        // Add contact to Resend audience (if audience ID configured)
        if (RESEND_AUDIENCE_ID) {
          await fetch(`https://api.resend.com/audiences/${RESEND_AUDIENCE_ID}/contacts`, {
            method: "POST",
            headers: {
              "Authorization": `Bearer ${RESEND_API_KEY}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              email,
              first_name: agencyName || "",
              unsubscribed: false,
            }),
          });
        }

        // Send welcome email
        await fetch("https://api.resend.com/emails", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${RESEND_API_KEY}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            from: "Agency OS <hello@agencyos.com.au>",
            to: [email],
            subject: "You're on the Agency OS waitlist! 🎉",
            html: `
              <!DOCTYPE html>
              <html>
                <head>
                  <meta charset="utf-8">
                  <meta name="viewport" content="width=device-width, initial-scale=1.0">
                </head>
                <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1d1d1f; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
                  <div style="text-align: center; margin-bottom: 40px;">
                    <div style="display: inline-flex; align-items: center; justify-content: center; width: 56px; height: 56px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); border-radius: 16px; margin-bottom: 16px;">
                      <span style="color: white; font-weight: bold; font-size: 20px;">A</span>
                    </div>
                    <h1 style="font-size: 28px; font-weight: 700; margin: 0; color: #111827;">Welcome to Agency OS</h1>
                  </div>
                  
                  <p style="font-size: 18px; color: #374151;">You're officially on the waitlist for Agency OS – the client acquisition machine built specifically for Australian marketing agencies.</p>
                  
                  <div style="background: linear-gradient(135deg, #fef3c7, #fde68a); border-radius: 16px; padding: 24px; margin: 32px 0; border: 1px solid #fcd34d;">
                    <h2 style="font-size: 16px; font-weight: 700; margin: 0 0 12px 0; color: #92400e;">🔥 Founding Member Status</h2>
                    <p style="margin: 0; color: #78350f; font-size: 15px;">You're in line for one of 20 founding spots at <strong>50% off for life</strong>. We'll reach out soon with your exclusive invite.</p>
                  </div>
                  
                  <div style="background: #f3f4f6; border-radius: 16px; padding: 24px; margin: 32px 0;">
                    <h2 style="font-size: 16px; font-weight: 700; margin: 0 0 16px 0; color: #111827;">What happens next?</h2>
                    <ul style="margin: 0; padding-left: 20px; color: #374151;">
                      <li style="margin-bottom: 12px;">We're onboarding <strong>20 founding agencies</strong> first</li>
                      <li style="margin-bottom: 12px;">You'll get early access before public launch</li>
                      <li style="margin-bottom: 12px;">Founding pricing is locked <strong>forever</strong> (even when we raise prices)</li>
                    </ul>
                  </div>

                  <div style="background: #f0f9ff; border-radius: 16px; padding: 24px; margin: 32px 0; border: 1px solid #bae6fd;">
                    <h2 style="font-size: 16px; font-weight: 700; margin: 0 0 12px 0; color: #0369a1;">What you'll get:</h2>
                    <ul style="margin: 0; padding-left: 20px; color: #0c4a6e; font-size: 14px;">
                      <li style="margin-bottom: 8px;">5-channel outreach (Email, SMS, LinkedIn, Voice AI, Direct Mail)</li>
                      <li style="margin-bottom: 8px;">AI-powered lead scoring (ALS Score™)</li>
                      <li style="margin-bottom: 8px;">Conversion Intelligence that learns what works</li>
                      <li style="margin-bottom: 8px;">Built specifically for Australian agencies</li>
                    </ul>
                  </div>
                  
                  <p style="font-size: 15px; color: #6b7280;">In the meantime, if you have questions or want to chat about your agency's outbound strategy, just reply to this email.</p>
                  
                  <p style="font-size: 16px; color: #111827; margin-top: 32px;">
                    Cheers,<br>
                    <strong>The Agency OS Team</strong><br>
                    <span style="color: #6b7280;">Melbourne, Australia 🇦🇺</span>
                  </p>
                  
                  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 40px 0 20px;">
                  <p style="font-size: 12px; color: #9ca3af; text-align: center;">
                    © 2025 Agency OS. You received this because you signed up at agencyos.com.au
                  </p>
                </body>
              </html>
            `,
          }),
        });
      } catch (resendError) {
        console.error("Resend API error:", resendError);
        // Continue anyway - the signup is still recorded
      }
    }

    // Log the signup
    console.log(`✅ Waitlist signup: ${email} from ${source} at ${new Date().toISOString()}`);

    return NextResponse.json({
      success: true,
      message: "Successfully joined the waitlist",
      redirect: "/waitlist/thank-you",
    });
  } catch (error) {
    console.error("Waitlist error:", error);
    return NextResponse.json(
      { error: "Something went wrong. Please try again." },
      { status: 500 }
    );
  }
}
