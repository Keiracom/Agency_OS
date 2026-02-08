/**
 * FILE: app/api/settings/icp/route.ts
 * PURPOSE: ICP (Ideal Customer Profile) configuration - GET and PUT
 * TODO: Replace mock data with Supabase settings table
 */

import { NextRequest, NextResponse } from "next/server";

// Types
export interface ICPConfig {
  id: string;
  name: string;
  description?: string;
  isDefault: boolean;
  criteria: {
    industries: string[];
    companySizes: string[]; // "1-10", "11-50", "51-200", "201-500", "500+"
    locations: string[];
    titles: string[];
    excludedTitles: string[];
    minRevenue?: number; // AUD
    maxRevenue?: number;
    technologies?: string[];
    signals?: string[]; // hiring, funding, expansion, etc.
  };
  scoring: {
    industryWeight: number;
    sizeWeight: number;
    titleWeight: number;
    signalWeight: number;
  };
  createdAt: string;
  updatedAt: string;
}

export interface ICPResponse {
  success: boolean;
  data: ICPConfig;
}

// Mock data - Default ICP for Australian marketing agencies
const mockICP: ICPConfig = {
  id: "icp_001",
  name: "Australian Marketing Agencies",
  description: "Primary target: mid-sized Australian marketing and creative agencies",
  isDefault: true,
  criteria: {
    industries: [
      "Marketing Agency",
      "Digital Marketing",
      "Creative Agency",
      "Advertising Agency",
      "PR Agency",
      "SEO Agency",
      "Social Media Agency",
    ],
    companySizes: ["11-50", "51-200"],
    locations: [
      "Sydney, Australia",
      "Melbourne, Australia",
      "Brisbane, Australia",
      "Perth, Australia",
      "Adelaide, Australia",
    ],
    titles: [
      "CEO",
      "Founder",
      "Managing Director",
      "Owner",
      "Director",
      "Head of Growth",
      "Business Development Director",
    ],
    excludedTitles: [
      "Intern",
      "Junior",
      "Assistant",
      "Coordinator",
      "Student",
    ],
    minRevenue: 500000,
    maxRevenue: 50000000,
    technologies: ["HubSpot", "Salesforce", "Google Ads", "Facebook Ads"],
    signals: ["hiring", "expansion", "new_funding", "new_office"],
  },
  scoring: {
    industryWeight: 30,
    sizeWeight: 25,
    titleWeight: 30,
    signalWeight: 15,
  },
  createdAt: "2024-01-15T00:00:00.000Z",
  updatedAt: new Date().toISOString(),
};

export async function GET() {
  try {
    // TODO: Supabase integration
    // const supabase = createClient(...)
    // const { data } = await supabase
    //   .from('icp_configs')
    //   .select('*')
    //   .eq('is_default', true)
    //   .single()

    return NextResponse.json({
      success: true,
      data: mockICP,
    } as ICPResponse);
  } catch (error) {
    console.error("ICP config GET error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch ICP config" },
      { status: 500 }
    );
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body: Partial<ICPConfig> = await request.json();

    // Validate required fields
    if (body.criteria) {
      if (!body.criteria.industries || body.criteria.industries.length === 0) {
        return NextResponse.json(
          { success: false, error: "At least one industry is required" },
          { status: 400 }
        );
      }
      if (!body.criteria.titles || body.criteria.titles.length === 0) {
        return NextResponse.json(
          { success: false, error: "At least one target title is required" },
          { status: 400 }
        );
      }
    }

    if (body.scoring) {
      const totalWeight =
        (body.scoring.industryWeight || 0) +
        (body.scoring.sizeWeight || 0) +
        (body.scoring.titleWeight || 0) +
        (body.scoring.signalWeight || 0);
      
      if (totalWeight !== 100) {
        return NextResponse.json(
          { success: false, error: "Scoring weights must sum to 100" },
          { status: 400 }
        );
      }
    }

    // TODO: Supabase integration
    // const supabase = createClient(...)
    // const { data, error } = await supabase
    //   .from('icp_configs')
    //   .update({
    //     ...body,
    //     updated_at: new Date().toISOString(),
    //   })
    //   .eq('id', body.id || mockICP.id)
    //   .select()
    //   .single()

    // Mock: merge updates with existing config
    const updatedConfig: ICPConfig = {
      ...mockICP,
      ...body,
      criteria: { ...mockICP.criteria, ...body.criteria },
      scoring: { ...mockICP.scoring, ...body.scoring },
      updatedAt: new Date().toISOString(),
    };

    console.log(`✅ ICP config updated: ${updatedConfig.name}`);

    return NextResponse.json({
      success: true,
      data: updatedConfig,
    } as ICPResponse);
  } catch (error) {
    console.error("ICP config PUT error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to update ICP config" },
      { status: 500 }
    );
  }
}
