/**
 * FILE: frontend/app/admin/settings/users/page.tsx
 * PURPOSE: User management for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Users
 */

"use client";

import { useState } from "react";
import { Search, MoreHorizontal, Eye, UserX, Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

interface User {
  id: string;
  name: string;
  email: string;
  clients: { name: string; role: string }[];
  lastActive: Date;
  status: "active" | "inactive" | "suspended";
  isPlatformAdmin: boolean;
}

// Mock data
const mockUsers: User[] = [
  {
    id: "1",
    name: "Dave Williams",
    email: "dave@agency.com",
    clients: [],
    lastActive: new Date(Date.now() - 1000 * 60 * 5),
    status: "active",
    isPlatformAdmin: true,
  },
  {
    id: "2",
    name: "John Smith",
    email: "john@leadgenpro.com",
    clients: [{ name: "LeadGen Pro", role: "owner" }],
    lastActive: new Date(Date.now() - 1000 * 60 * 30),
    status: "active",
    isPlatformAdmin: false,
  },
  {
    id: "3",
    name: "Sarah Johnson",
    email: "sarah@growthlab.co",
    clients: [{ name: "GrowthLab", role: "owner" }],
    lastActive: new Date(Date.now() - 1000 * 60 * 60 * 2),
    status: "active",
    isPlatformAdmin: false,
  },
  {
    id: "4",
    name: "Mike Wilson",
    email: "mike@scaleup.io",
    clients: [{ name: "ScaleUp Co", role: "admin" }],
    lastActive: new Date(Date.now() - 1000 * 60 * 60 * 24),
    status: "active",
    isPlatformAdmin: false,
  },
  {
    id: "5",
    name: "Lisa Brown",
    email: "lisa@enterprise.com",
    clients: [
      { name: "Enterprise Co", role: "owner" },
      { name: "Marketing Plus", role: "admin" },
    ],
    lastActive: new Date(Date.now() - 1000 * 60 * 60 * 48),
    status: "active",
    isPlatformAdmin: false,
  },
  {
    id: "6",
    name: "Bob Chen",
    email: "bob@leadgenpro.com",
    clients: [{ name: "LeadGen Pro", role: "member" }],
    lastActive: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7),
    status: "inactive",
    isPlatformAdmin: false,
  },
  {
    id: "7",
    name: "Alice Wong",
    email: "alice@suspended.com",
    clients: [{ name: "Suspended Co", role: "owner" }],
    lastActive: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30),
    status: "suspended",
    isPlatformAdmin: false,
  },
];

const roleColors: Record<string, string> = {
  owner: "bg-purple-500/10 text-purple-700 border-purple-500/20",
  admin: "bg-blue-500/10 text-blue-700 border-blue-500/20",
  member: "bg-green-500/10 text-green-700 border-green-500/20",
  viewer: "bg-gray-500/10 text-gray-700 border-gray-500/20",
};

const statusColors = {
  active: "bg-green-500/10 text-green-700 border-green-500/20",
  inactive: "bg-yellow-500/10 text-yellow-700 border-yellow-500/20",
  suspended: "bg-red-500/10 text-red-700 border-red-500/20",
};

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return `${Math.floor(seconds / 604800)}w ago`;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export default function AdminUsersPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const filteredUsers = mockUsers.filter((user) => {
    const matchesSearch =
      user.name.toLowerCase().includes(search.toLowerCase()) ||
      user.email.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || user.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const activeCount = mockUsers.filter((u) => u.status === "active").length;
  const adminCount = mockUsers.filter((u) => u.isPlatformAdmin).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Users</h1>
        <p className="text-muted-foreground">
          Manage all users across all clients
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Users
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockUsers.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Active Users
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{activeCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Platform Admins
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">{adminCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Suspended
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {mockUsers.filter((u) => u.status === "suspended").length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search users..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="suspended">Suspended</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Client(s)</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Active</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredUsers.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback>{getInitials(user.name)}</AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{user.name}</span>
                          {user.isPlatformAdmin && (
                            <Badge
                              variant="outline"
                              className="bg-purple-500/10 text-purple-700 flex items-center gap-1"
                            >
                              <Shield className="h-3 w-3" />
                              Admin
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">{user.email}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {user.clients.length === 0 ? (
                      <span className="text-muted-foreground">-</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {user.clients.map((client, i) => (
                          <Badge key={i} variant="outline" className={roleColors[client.role]}>
                            {client.name} ({client.role})
                          </Badge>
                        ))}
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={statusColors[user.status]}>
                      {user.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatTimeAgo(user.lastActive)}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem>
                          <Eye className="mr-2 h-4 w-4" />
                          View Details
                        </DropdownMenuItem>
                        {!user.isPlatformAdmin && (
                          <>
                            <DropdownMenuItem>
                              <Shield className="mr-2 h-4 w-4" />
                              Make Admin
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem className="text-red-600">
                              <UserX className="mr-2 h-4 w-4" />
                              {user.status === "suspended" ? "Unsuspend" : "Suspend"}
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
