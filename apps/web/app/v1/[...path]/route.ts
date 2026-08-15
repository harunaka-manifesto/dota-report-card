import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade"
]);

function apiBaseUrl(): URL | null {
  const configured = process.env.API_BASE_URL?.trim();
  if (!configured) return null;
  try {
    return new URL(configured.endsWith("/") ? configured : configured + "/");
  } catch {
    return null;
  }
}

async function proxy(
  request: NextRequest,
  { params }: { params: { path: string[] } }
): Promise<Response> {
  const baseUrl = apiBaseUrl();
  if (!baseUrl) {
    return NextResponse.json(
      {
        code: "API_NOT_CONFIGURED",
        message: "The report service is not configured. Set API_BASE_URL on the web deployment."
      },
      { status: 503 }
    );
  }

  const target = new URL(`v1/${params.path.map(encodeURIComponent).join("/")}`, baseUrl);
  target.search = request.nextUrl.search;

  const headers = new Headers(request.headers);
  for (const header of HOP_BY_HOP_HEADERS) headers.delete(header);

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.arrayBuffer(),
      cache: "no-store",
      redirect: "manual"
    });
    const responseHeaders = new Headers(upstream.headers);
    for (const header of HOP_BY_HOP_HEADERS) responseHeaders.delete(header);
    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders
    });
  } catch {
    return NextResponse.json(
      {
        code: "API_UNAVAILABLE",
        message: "The report service is temporarily unreachable. Check API_BASE_URL and the API deployment."
      },
      { status: 502 }
    );
  }
}

export const GET = proxy;
export const POST = proxy;
