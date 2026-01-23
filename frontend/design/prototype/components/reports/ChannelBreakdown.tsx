"use client";

import { Mail, MessageSquare, Linkedin, Phone, Send } from "lucide-react";
import { LucideIcon } from "lucide-react";

/**
 * Channel metrics data
 */
export interface ChannelMetrics {
  channel: "email" | "sms" | "linkedin" | "voice" | "mail";
  sent: number;
  delivered: number;
  opened: number;
  replied: number;
  meetings: number;
}

/**
 * ChannelBreakdown props
 */
export interface ChannelBreakdownProps {
  /** Array of channel metrics */
  channels: ChannelMetrics[];
}

/**
 * Channel configuration with icons and colors
 */
const channelConfig: Record<
  string,
  { icon: LucideIcon; color: string; label: string }
> = {
  email: { icon: Mail, color: "#3B82F6", label: "Email" },
  sms: { icon: MessageSquare, color: "#10B981", label: "SMS" },
  linkedin: { icon: Linkedin, color: "#0077B5", label: "LinkedIn" },
  voice: { icon: Phone, color: "#8B5CF6", label: "Voice" },
  mail: { icon: Send, color: "#F59E0B", label: "Direct Mail" },
};

/**
 * ChannelBreakdown - Channel performance table component
 *
 * Features:
 * - Table view with all channels
 * - Columns: Channel, Sent, Delivered, Opened, Replied, Meetings
 * - Percentage columns for rates
 * - Channel icons with colors
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Background: #FFFFFF (card-bg)
 * - Border: #E2E8F0 (card-border)
 * - Text primary: #1E293B
 * - Text secondary: #64748B
 */
export function ChannelBreakdown({ channels }: ChannelBreakdownProps) {
  // Calculate percentages
  const getRate = (numerator: number, denominator: number) => {
    if (denominator === 0) return "0%";
    return `${Math.round((numerator / denominator) * 100)}%`;
  };

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-[#E2E8F0]">
        <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
          Channel Performance
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-[#F8FAFC]">
              <th className="px-6 py-3 text-left text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Channel
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Sent
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Delivered
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Delivery Rate
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Opened
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Open Rate
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Replied
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Reply Rate
              </th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-[#64748B] uppercase tracking-wider">
                Meetings
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E2E8F0]">
            {channels.map((channel) => {
              const config = channelConfig[channel.channel];
              const Icon = config.icon;

              return (
                <tr
                  key={channel.channel}
                  className="hover:bg-[#F8FAFC] transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div
                        className="p-2 rounded-lg"
                        style={{ backgroundColor: `${config.color}15` }}
                      >
                        <Icon
                          className="h-4 w-4"
                          style={{ color: config.color }}
                        />
                      </div>
                      <span className="text-sm font-medium text-[#1E293B]">
                        {config.label}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right text-sm text-[#1E293B]">
                    {channel.sent.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-right text-sm text-[#1E293B]">
                    {channel.delivered.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-right text-sm text-[#64748B]">
                    {getRate(channel.delivered, channel.sent)}
                  </td>
                  <td className="px-6 py-4 text-right text-sm text-[#1E293B]">
                    {channel.opened.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-right text-sm text-[#64748B]">
                    {getRate(channel.opened, channel.delivered)}
                  </td>
                  <td className="px-6 py-4 text-right text-sm text-[#1E293B]">
                    {channel.replied.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-right text-sm text-[#64748B]">
                    {getRate(channel.replied, channel.delivered)}
                  </td>
                  <td className="px-6 py-4 text-right text-sm font-semibold text-[#1E293B]">
                    {channel.meetings}
                  </td>
                </tr>
              );
            })}
          </tbody>
          {/* Totals row */}
          <tfoot>
            <tr className="bg-[#F8FAFC] border-t-2 border-[#E2E8F0]">
              <td className="px-6 py-4">
                <span className="text-sm font-semibold text-[#1E293B]">
                  Total
                </span>
              </td>
              <td className="px-6 py-4 text-right text-sm font-semibold text-[#1E293B]">
                {channels
                  .reduce((sum, c) => sum + c.sent, 0)
                  .toLocaleString()}
              </td>
              <td className="px-6 py-4 text-right text-sm font-semibold text-[#1E293B]">
                {channels
                  .reduce((sum, c) => sum + c.delivered, 0)
                  .toLocaleString()}
              </td>
              <td className="px-6 py-4 text-right text-sm font-semibold text-[#64748B]">
                {getRate(
                  channels.reduce((sum, c) => sum + c.delivered, 0),
                  channels.reduce((sum, c) => sum + c.sent, 0)
                )}
              </td>
              <td className="px-6 py-4 text-right text-sm font-semibold text-[#1E293B]">
                {channels
                  .reduce((sum, c) => sum + c.opened, 0)
                  .toLocaleString()}
              </td>
              <td className="px-6 py-4 text-right text-sm font-semibold text-[#64748B]">
                {getRate(
                  channels.reduce((sum, c) => sum + c.opened, 0),
                  channels.reduce((sum, c) => sum + c.delivered, 0)
                )}
              </td>
              <td className="px-6 py-4 text-right text-sm font-semibold text-[#1E293B]">
                {channels
                  .reduce((sum, c) => sum + c.replied, 0)
                  .toLocaleString()}
              </td>
              <td className="px-6 py-4 text-right text-sm font-semibold text-[#64748B]">
                {getRate(
                  channels.reduce((sum, c) => sum + c.replied, 0),
                  channels.reduce((sum, c) => sum + c.delivered, 0)
                )}
              </td>
              <td className="px-6 py-4 text-right text-sm font-bold text-[#1E293B]">
                {channels.reduce((sum, c) => sum + c.meetings, 0)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

export default ChannelBreakdown;
