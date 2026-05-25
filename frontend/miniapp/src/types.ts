export type TabId = "catalog" | "purchases" | "support" | "admin";

export type PurchaseType = "lecture" | "block" | "section";

export type PurchaseStatus = "pending" | "paid" | "canceled" | "refunded";

export type PaymentStatus =
  | "pending"
  | "succeeded"
  | "canceled"
  | "waiting_for_capture"
  | "failed";

export type ContentType = "pdf" | "video" | "audio" | "image" | "text";

export type ContentDeliveryMethod =
  | "inline_text"
  | "backend_file"
  | "telegram_file_id"
  | "unavailable";

export type SupportRequestStatus = "open" | "in_progress" | "closed";

export interface MiniAppMeta {
  app_name: string;
  api_version: string;
  miniapp_url: string;
  auth_header: string;
  frontend_status: "planned" | "scaffolded" | "available";
  features: string[];
}

export interface MiniAppUser {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  is_admin: boolean;
}

export interface Section {
  id: number;
  title: string;
  description: string | null;
}

export interface Block {
  id: number;
  section_id: number;
  title: string;
  description: string | null;
  price: string;
  has_access: boolean;
}

export interface Lecture {
  id: number;
  block_id: number;
  title: string;
  short_description: string | null;
  full_description: string | null;
  price: string;
  has_access: boolean;
}

export interface Purchase {
  id: number;
  purchase_type: PurchaseType;
  object_id: number;
  price: string;
  status: PurchaseStatus;
  created_at: string | null;
}

export interface CreatePaymentResponse {
  purchase: Purchase;
  confirmation_url: string | null;
  status: PurchaseStatus;
  payment_status: PaymentStatus | null;
  payment_error: boolean;
  message: string;
}

export interface CheckPaymentResponse {
  provider_payment_id: string;
  payment_status: PaymentStatus;
  handled: boolean;
  purchase_id: number | null;
  granted_count: number;
  is_paid: boolean;
  message: string;
}

export interface PurchasedLecture {
  id: number;
  title: string;
  short_description: string | null;
  purchased_at: string;
  source_purchase_id: number | null;
}

export interface ContentItem {
  id: number;
  lecture_id: number;
  type: ContentType;
  title: string;
  protected_content_enabled: boolean;
  delivery_method: ContentDeliveryMethod;
  is_text_available_inline: boolean;
  is_file_available: boolean;
  file_url: string | null;
  text_content: string | null;
}

export interface LectureContentResponse {
  lecture: PurchasedLecture;
  content_items: ContentItem[];
}

export interface SupportRequest {
  id: number;
  message: string;
  status: SupportRequestStatus;
  created_at: string;
}
