import { NextRequest, NextResponse } from "next/server";
import Retell from "retell-sdk";

const retellClient = new Retell({
  apiKey: process.env.RETELL_API_KEY || "",
});

export async function POST(request: NextRequest) {
  try {
    const { patientName, dob, insuranceId } = await request.json();

    if (!patientName || !dob || !insuranceId) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      );
    }

    const agentId = process.env.RETELL_AGENT_ID;
    if (!agentId) {
      return NextResponse.json(
        { error: "Agent ID not configured" },
        { status: 500 }
      );
    }

    const callResponse = await retellClient.call.createWebCall({
      agent_id: agentId,
      metadata: {
        patient_name: patientName,
        dob,
        insurance_id: insuranceId,
      },
      retell_llm_dynamic_variables: {
        patient_name: patientName,
        dob,
        insurance_id: insuranceId,
      },
    });

    return NextResponse.json({
      accessToken: callResponse.access_token,
      callId: callResponse.call_id,
    });
  } catch (error) {
    console.error("Error creating web call:", error);
    return NextResponse.json(
      { error: "Failed to create call" },
      { status: 500 }
    );
  }
}
