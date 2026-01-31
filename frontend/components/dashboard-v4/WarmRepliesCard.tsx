/**
 * FILE: frontend/components/dashboard-v4/WarmRepliesCard.tsx
 * PURPOSE: Card showing warm replies that need action
 * PHASE: Dashboard V4 Implementation
 */

"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { WarmReply } from "./types";

interface WarmRepliesCardProps {
  replies: WarmReply[];
}

function ReplyItem({ reply }: { reply: WarmReply }) {
  return (
    <div className="flex items-center gap-3 py-3 border-b last:border-b-0">
      <Avatar className="h-10 w-10">
        <AvatarFallback className="bg-muted text-muted-foreground font-semibold">
          {reply.initials}
        </AvatarFallback>
      </Avatar>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-foreground truncate">
          {reply.name} • {reply.company}
        </p>
        <p className="text-sm text-muted-foreground truncate">
          &quot;{reply.preview}&quot;
        </p>
      </div>
      <Link href={`/dashboard/replies?lead=${reply.leadId}`}>
        <Button size="sm" className="flex-shrink-0">
          Reply
        </Button>
      </Link>
    </div>
  );
}

export function WarmRepliesCard({ replies }: WarmRepliesCardProps) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center gap-3">
          <Badge className="bg-emerald-500 hover:bg-emerald-500 text-white px-3 py-1 text-sm font-bold">
            {replies.length}
          </Badge>
          <h3 className="font-semibold text-foreground">Warm replies to review</h3>
        </div>
      </CardHeader>
      <CardContent>
        {replies.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No warm replies waiting. Great job staying on top of things!
          </p>
        ) : (
          <div>
            {replies.map((reply) => (
              <ReplyItem key={reply.id} reply={reply} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
