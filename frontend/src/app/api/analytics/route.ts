import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:7860";

/**
 * Proxy GET requests to the backend /analytics endpoints.
 */
export async function GET(request: NextRequest) {
  try {
    // Get the path after /api/analytics
    const url = new URL(request.url);
    const pathAfterAnalytics = url.pathname.replace("/api/analytics", "");
    const searchParams = url.searchParams.toString();

    // Build backend URL
    const backendPath = `/analytics${pathAfterAnalytics}`;
    const backendUrl = `${BACKEND_URL}${backendPath}${
      searchParams ? `?${searchParams}` : ""
    }`;

    const response = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: errorText || "Backend request failed" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Analytics API proxy error:", error);
    return NextResponse.json(
      { error: "Failed to connect to backend" },
      { status: 503 }
    );
  }
}

/**
 * Proxy POST requests to the backend /analytics endpoints.
 */
export async function POST(request: NextRequest) {
  try {
    // Get the path after /api/analytics
    const url = new URL(request.url);
    const pathAfterAnalytics = url.pathname.replace("/api/analytics", "");

    // Build backend URL
    const backendPath = `/analytics${pathAfterAnalytics}`;
    const backendUrl = `${BACKEND_URL}${backendPath}`;

    // Forward the request body
    const body = await request.json();

    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: errorText || "Backend request failed" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Analytics API proxy error:", error);
    return NextResponse.json(
      { error: "Failed to connect to backend" },
      { status: 503 }
    );
  }
}
