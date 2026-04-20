#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { createClient } from "@supabase/supabase-js";
import { config } from "dotenv";
import { resolve } from "path";
import { homedir } from "os";
import { randomUUID } from "crypto";

config({ path: resolve(homedir(), ".config/agency-os/.env") });

const SUPABASE_URL = process.env.SUPABASE_URL || "";
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || "";
const OPENAI_API_KEY = process.env.OPENAI_API_KEY || "";

const EMBEDDING_MODEL = "text-embedding-3-small";
const EMBEDDING_DIMENSIONS = 1536;
const DEFAULT_MATCH_THRESHOLD = 0.25;
const DEFAULT_LIMIT = 10;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
  db: { schema: "public" },
});

async function getEmbedding(text: string): Promise<number[]> {
  const response = await fetch("https://api.openai.com/v1/embeddings", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${OPENAI_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: EMBEDDING_MODEL,
      input: text,
      dimensions: EMBEDDING_DIMENSIONS,
    }),
  });

  if (!response.ok) {
    throw new Error(`OpenAI API error: ${response.status}`);
  }

  const data = await response.json();
  return data.data[0].embedding;
}

async function searchMemories(query: string, limit = DEFAULT_LIMIT, minScore = DEFAULT_MATCH_THRESHOLD) {
  const embedding = await getEmbedding(query);
  
  const { data, error } = await supabase.rpc("match_agent_memories", {
    query_embedding: embedding,
    match_threshold: minScore,
    match_count: limit,
  });

  if (error) {
    // Fallback: direct query without vector search
    const { data: fallbackData, error: fallbackError } = await supabase
      .from("agent_memories")
      .select("id, content, source_type, typed_metadata, tags, created_at, callsign, state, access_count")
      .in("state", ["confirmed", "tentative"])
      .limit(limit);
    
    if (fallbackError) throw fallbackError;
    return fallbackData || [];
  }

  return data || [];
}

async function saveMemory(content: string, type?: string, metadata?: Record<string, unknown>) {
  const embedding = await getEmbedding(content);
  const id = randomUUID();

  const { data, error } = await supabase
    .from("agent_memories")
    .insert({
      id,
      content,
      source_type: type || "conversation",
      embedding,
      typed_metadata: metadata || {},
      callsign: process.env.CALLSIGN || "elliot",
      tags: [],
      state: "tentative",
      valid_from: new Date().toISOString(),
    })
    .select("id, created_at")
    .single();

  if (error) throw error;

  return {
    status: "saved",
    id: data.id,
    content_preview: content.length > 200 ? content.slice(0, 200) + "..." : content,
    type: type || "conversation",
    created_at: data.created_at,
  };
}

async function listRecentMemories(hours = 24, limit = DEFAULT_LIMIT) {
  const cutoff = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();

  const { data, error } = await supabase
    .from("agent_memories")
    .select("id, content, source_type, typed_metadata, tags, created_at, callsign, state, access_count")
    .in("state", ["confirmed", "tentative"])
    .gte("created_at", cutoff)
    .order("created_at", { ascending: false })
    .limit(limit);

  if (error) throw error;
  return data || [];
}

async function getMemoryById(memoryId: string) {
  const { data, error } = await supabase
    .from("agent_memories")
    .select("id, content, source_type, typed_metadata, tags, created_at, callsign, state, access_count")
    .eq("id", memoryId)
    .in("state", ["confirmed", "tentative"])
    .single();

  if (error) return null;
  return data;
}

async function deleteMemory(memoryId: string) {
  // Soft delete
  const { data, error } = await supabase
    .from("agent_memories")
    .update({ state: "archived" })
    .eq("id", memoryId)
    .select("id")
    .single();

  if (error) return { status: "not_found", id: memoryId };
  return { status: "deleted", id: data.id };
}

async function getMemoryStats() {
  const { count: total } = await supabase
    .from("agent_memories")
    .select("*", { count: "exact", head: true })
    .in("state", ["confirmed", "tentative"]);

  const { data: byType } = await supabase
    .from("agent_memories")
    .select("source_type")
    .in("state", ["confirmed", "tentative"])
    .not("source_type", "is", null);

  const typeCounts: Record<string, number> = {};
  (byType || []).forEach((row) => {
    const t = row.source_type || "unknown";
    typeCounts[t] = (typeCounts[t] || 0) + 1;
  });

  const last24h = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
  const { count: recent24h } = await supabase
    .from("agent_memories")
    .select("*", { count: "exact", head: true })
    .in("state", ["confirmed", "tentative"])
    .gte("created_at", last24h);

  const last7d = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
  const { count: recent7d } = await supabase
    .from("agent_memories")
    .select("*", { count: "exact", head: true })
    .in("state", ["confirmed", "tentative"])
    .gte("created_at", last7d);

  return {
    total: total || 0,
    by_type: typeCounts,
    last_24h: recent24h || 0,
    last_7d: recent7d || 0,
  };
}

async function searchByType(type: string, limit = DEFAULT_LIMIT) {
  const { data, error } = await supabase
    .from("agent_memories")
    .select("id, content, source_type, typed_metadata, tags, created_at, callsign, state, access_count")
    .eq("source_type", type)
    .in("state", ["confirmed", "tentative"])
    .order("created_at", { ascending: false })
    .limit(limit);

  if (error) throw error;
  return data || [];
}

const server = new Server(
  { name: "memory-mcp", version: "1.1.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "search",
      description: "Semantic search over memories using vector similarity. Returns memories ranked by relevance.",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search query text" },
          limit: { type: "number", description: "Maximum results (default: 10)" },
          min_score: { type: "number", description: "Minimum similarity score 0-1 (default: 0.25)" },
        },
        required: ["query"],
      },
    },
    {
      name: "save",
      description: "Save a new memory with auto-generated embedding for semantic search.",
      inputSchema: {
        type: "object",
        properties: {
          content: { type: "string", description: "Memory content to save" },
          type: { type: "string", description: "Type of memory (e.g., 'conversation', 'decision', 'fact')" },
          metadata: { type: "object", description: "Optional metadata JSON" },
        },
        required: ["content"],
      },
    },
    {
      name: "list_recent",
      description: "List recently created memories within a time window.",
      inputSchema: {
        type: "object",
        properties: {
          hours: { type: "number", description: "Look back hours (default: 24)" },
          limit: { type: "number", description: "Maximum results (default: 10)" },
        },
      },
    },
    {
      name: "get_by_id",
      description: "Get a specific memory by its UUID.",
      inputSchema: {
        type: "object",
        properties: {
          memory_id: { type: "string", description: "UUID of the memory" },
        },
        required: ["memory_id"],
      },
    },
    {
      name: "delete",
      description: "Delete a memory by its UUID (soft delete).",
      inputSchema: {
        type: "object",
        properties: {
          memory_id: { type: "string", description: "UUID of the memory to delete" },
        },
        required: ["memory_id"],
      },
    },
    {
      name: "get_stats",
      description: "Get memory statistics including counts by type and recent activity.",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "search_by_type",
      description: "Find memories with a specific type.",
      inputSchema: {
        type: "object",
        properties: {
          type: { type: "string", description: "Type to search for" },
          limit: { type: "number", description: "Maximum results (default: 10)" },
        },
        required: ["type"],
      },
    },
  ],
}));

// Helper to serialize errors properly
function serializeError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "object" && error !== null) {
    // Handle Supabase/PostgrestError and other complex error objects
    const e = error as Record<string, unknown>;
    if (e.message) return String(e.message);
    if (e.error) return String(e.error);
    if (e.details) return String(e.details);
    try {
      return JSON.stringify(error);
    } catch {
      return "Unknown error (could not serialize)";
    }
  }
  return String(error);
}

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "search": {
        const result = await searchMemories(
          args?.query as string,
          (args?.limit as number) || DEFAULT_LIMIT,
          (args?.min_score as number) || DEFAULT_MATCH_THRESHOLD
        );
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "save": {
        const result = await saveMemory(
          args?.content as string,
          args?.type as string,
          args?.metadata as Record<string, unknown>
        );
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "list_recent": {
        const result = await listRecentMemories(
          (args?.hours as number) || 24,
          (args?.limit as number) || DEFAULT_LIMIT
        );
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_by_id": {
        const result = await getMemoryById(args?.memory_id as string);
        if (!result) {
          return { content: [{ type: "text", text: JSON.stringify({ status: "not_found", id: args?.memory_id }, null, 2) }] };
        }
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "delete": {
        const result = await deleteMemory(args?.memory_id as string);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "get_stats": {
        const result = await getMemoryStats();
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      case "search_by_type": {
        const result = await searchByType(
          args?.type as string,
          (args?.limit as number) || DEFAULT_LIMIT
        );
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [{ type: "text", text: `Error: ${serializeError(error)}` }],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Memory MCP server running on stdio");
}

main().catch(console.error);
