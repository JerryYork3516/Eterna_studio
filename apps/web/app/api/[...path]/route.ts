import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

function normalizeBaseUrl(value: string) {
  return value.replace(/\/+$/, "");
}

async function proxyRequest(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  if (!API_BASE) {
    return NextResponse.json(
      { detail: "Missing API_BASE_URL or NEXT_PUBLIC_API_BASE_URL" },
      { status: 503 }
    );
  }

  const { path = [] } = await context.params;
  const upstreamUrl = new URL(`/${path.join("/")}${request.nextUrl.search}`, normalizeBaseUrl(API_BASE));
  const headers = new Headers(request.headers);
  headers.delete("host");

  const response = await fetch(upstreamUrl, {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer(),
    cache: "no-store"
  });
  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");
  responseHeaders.delete("transfer-encoding");

  return new NextResponse(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders
  });
}

export function GET(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  return proxyRequest(request, context);
}

export function POST(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  return proxyRequest(request, context);
}
