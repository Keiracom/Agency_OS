/**
 * FILE: scripts/v0-generate.ts
 * PURPOSE: Helper script to generate UI components via v0.dev Platform API
 * PHASE: 21
 * USAGE: npx ts-node scripts/v0-generate.ts <prompt-file> <output-dir>
 */

import * as fs from 'fs'
import * as path from 'path'
import * as dotenv from 'dotenv'

// Load env from config/.env
dotenv.config({ path: path.resolve(__dirname, '../config/.env') })

interface GenerateOptions {
  prompt: string
  outputDir: string
  iterate?: string[]  // Follow-up prompts for refinement
}

// Design system context to include in all prompts
const DESIGN_SYSTEM = `
You are an expert React/TypeScript/Tailwind developer building for Agency OS.

DESIGN SYSTEM RULES:
- Dark theme default: #0a0a0f (primary bg), #0f0f13 (card bg)
- Glass morphism: backdrop-blur-[20px], border border-white/10, bg-white/5
- Max border-radius: 8px (no pills except badges)
- Gradients: from-blue-500 to-purple-600
- Text: white (primary), white/70 (secondary), white/50 (muted)
- Compact spacing: p-3 to p-4 on cards
- Use lucide-react for icons
- Export components as default with TypeScript types
- Include proper TypeScript interfaces for all props
- Make all data configurable via props with sensible defaults
- Add responsive breakpoints (stack on mobile < 640px)
`

async function generate(options: GenerateOptions): Promise<string> {
  const { prompt, outputDir, iterate = [] } = options

  // Ensure output directory exists
  fs.mkdirSync(outputDir, { recursive: true })

  const apiKey = process.env.V0_API_KEY
  if (!apiKey) {
    throw new Error('V0_API_KEY not found in environment. Check config/.env')
  }

  // Import v0-sdk dynamically (ES module)
  const { v0 } = await import('v0-sdk')

  console.log('🚀 Generating with v0.dev...')
  console.log('📝 Prompt preview:', prompt.substring(0, 200) + '...')

  // Create initial chat with design system context
  const chat = await v0.chats.create({
    message: prompt,
    system: DESIGN_SYSTEM
  })

  console.log(`\n🌐 Web URL: ${chat.webUrl}`)
  console.log(`📺 Preview URL: ${chat.latestVersion?.demoUrl || 'pending...'}`)
  console.log(`🔑 Chat ID: ${chat.id}`)

  // Wait for completion if status is pending
  let currentChat = chat
  let attempts = 0
  const maxAttempts = 30 // 30 seconds max wait

  while (currentChat.latestVersion?.status === 'pending' && attempts < maxAttempts) {
    console.log(`⏳ Generation in progress... (${attempts + 1}/${maxAttempts})`)
    await new Promise(resolve => setTimeout(resolve, 1000))
    currentChat = await v0.chats.getById({ chatId: chat.id })
    attempts++
  }

  if (currentChat.latestVersion?.status === 'failed') {
    throw new Error('Generation failed. Check the web URL for details.')
  }

  // Apply iterations if provided
  for (let i = 0; i < iterate.length; i++) {
    const followUp = iterate[i]
    console.log(`\n🔄 Iteration ${i + 1}: ${followUp.substring(0, 50)}...`)

    const response = await v0.chats.sendMessage({
      chatId: chat.id,
      message: followUp
    })

    // Wait for iteration to complete
    attempts = 0
    currentChat = await v0.chats.getById({ chatId: chat.id })
    while (currentChat.latestVersion?.status === 'pending' && attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 1000))
      currentChat = await v0.chats.getById({ chatId: chat.id })
      attempts++
    }

    if (currentChat.latestVersion?.demoUrl) {
      console.log(`📺 Updated preview: ${currentChat.latestVersion.demoUrl}`)
    }
  }

  // Get final chat state with files
  currentChat = await v0.chats.getById({ chatId: chat.id })
  const files = currentChat.latestVersion?.files

  // Write generated files
  if (files && files.length > 0) {
    console.log(`\n✅ Writing ${files.length} file(s):`)

    files.forEach((file: { name: string; content: string }) => {
      const filePath = path.join(outputDir, file.name)
      fs.writeFileSync(filePath, file.content, 'utf-8')
      console.log(`   📄 ${filePath}`)
    })
  } else {
    console.log('\n⚠️  No files in response. Check the web URL for output.')
    console.log(`   ${currentChat.webUrl}`)
  }

  return chat.id
}

// CLI interface
async function main() {
  const args = process.argv.slice(2)

  if (args.length < 2) {
    console.log(`
Usage: npx ts-node scripts/v0-generate.ts <prompt-file> <output-dir> [--iterate "follow-up prompt"]

Examples:
  npx ts-node scripts/v0-generate.ts prompts/hero.txt frontend/components/generated/
  npx ts-node scripts/v0-generate.ts prompts/hero.txt frontend/components/landing/ --iterate "make spacing more compact"

Options:
  --iterate    Add a follow-up prompt to refine the generation (can be used multiple times)
  --help       Show this help message
`)
    process.exit(1)
  }

  const promptFile = args[0]
  const outputDir = args[1]

  // Parse iteration flags
  const iterate: string[] = []
  for (let i = 2; i < args.length; i++) {
    if (args[i] === '--iterate' && args[i + 1]) {
      iterate.push(args[i + 1])
      i++ // Skip next arg
    }
  }

  // Read prompt from file
  if (!fs.existsSync(promptFile)) {
    console.error(`❌ Prompt file not found: ${promptFile}`)
    process.exit(1)
  }

  const prompt = fs.readFileSync(promptFile, 'utf-8')

  try {
    const chatId = await generate({ prompt, outputDir, iterate })
    console.log(`\n✨ Done! Chat ID: ${chatId}`)
    console.log(`   Use this ID to continue the conversation if needed.`)
  } catch (error) {
    console.error('\n❌ Generation failed:', error)
    process.exit(1)
  }
}

main()
