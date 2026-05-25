import { getTelegramInitData } from "./telegram";
import type {
  Block,
  CheckPaymentResponse,
  ContentItem,
  CreatePaymentResponse,
  Lecture,
  LectureContentResponse,
  MiniAppMeta,
  MiniAppUser,
  PurchasedLecture,
  PurchaseType,
  Section,
  SupportRequest,
} from "../types";

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  const initData = getTelegramInitData();

  if (initData) {
    headers.set("X-Telegram-Init-Data", initData);
  }
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    ...init,
    headers,
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return (await response.json()) as T;
}

export function fetchMiniAppMeta(): Promise<MiniAppMeta> {
  return apiRequest<MiniAppMeta>("/miniapp/api/meta");
}

export function fetchMiniAppUser(): Promise<MiniAppUser> {
  return apiRequest<MiniAppUser>("/miniapp/api/auth/me");
}

export function fetchSections(): Promise<Section[]> {
  return apiRequest<Section[]>("/miniapp/api/catalog/sections");
}

export function fetchBlocks(sectionId: number): Promise<Block[]> {
  return apiRequest<Block[]>(`/miniapp/api/catalog/sections/${sectionId}/blocks`);
}

export function fetchLectures(blockId: number): Promise<Lecture[]> {
  return apiRequest<Lecture[]>(`/miniapp/api/catalog/blocks/${blockId}/lectures`);
}

export function createPurchase(input: {
  purchaseType: PurchaseType;
  objectId: number;
}): Promise<CreatePaymentResponse> {
  return apiRequest<CreatePaymentResponse>("/miniapp/api/purchases", {
    method: "POST",
    body: JSON.stringify({
      purchase_type: input.purchaseType,
      object_id: input.objectId,
    }),
  });
}

export function checkPayment(purchaseId: number): Promise<CheckPaymentResponse> {
  return apiRequest<CheckPaymentResponse>(`/miniapp/api/payments/${purchaseId}/check`, {
    method: "POST",
  });
}

export function fetchMyPurchases(): Promise<PurchasedLecture[]> {
  return apiRequest<PurchasedLecture[]>("/miniapp/api/purchases/my");
}

export function fetchLectureContent(lectureId: number): Promise<LectureContentResponse> {
  return apiRequest<LectureContentResponse>(`/miniapp/api/content/lectures/${lectureId}`);
}

export async function fetchContentFileBlob(item: ContentItem): Promise<Blob> {
  if (!item.file_url) {
    throw new Error("Файл недоступен внутри Mini App.");
  }

  return apiBlobRequest(item.file_url);
}

export function fetchSupportRequests(): Promise<SupportRequest[]> {
  return apiRequest<SupportRequest[]>("/miniapp/api/support/requests");
}

export function createSupportRequest(message: string): Promise<SupportRequest> {
  return apiRequest<SupportRequest>("/miniapp/api/support/requests", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

async function apiBlobRequest(path: string, init?: RequestInit): Promise<Blob> {
  const headers = new Headers(init?.headers);
  const initData = getTelegramInitData();

  if (initData) {
    headers.set("X-Telegram-Init-Data", initData);
  }

  const response = await fetch(path, {
    ...init,
    headers,
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return response.blob();
}

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // Response body is optional for API errors.
  }

  return `API request failed: ${response.status}`;
}
