'use client';

import { ChannelType, channelEmoji } from './types';

interface Props {
  channels: ChannelType[];
}

export function CampaignChannels({ channels }: Props) {
  return (
    <span className="text-base">
      {channels.map(ch => channelEmoji[ch]).join(' ')}
    </span>
  );
}
