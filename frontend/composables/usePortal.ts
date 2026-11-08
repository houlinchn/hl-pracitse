export type Account = {
  id: string;
  email: string;
  role: "applicant" | "staff";
  permissions: string[];
};
export type Status = "draft" | "submitted" | "screening";
export type StatusEvent = {
  id: string;
  actor_id: string;
  delegated_by: string | null;
  channel: string;
  before: Status | null;
  after: Status;
  reason: string;
  at: string;
};
export type Application = {
  id: string;
  applicant_id: string;
  name: string;
  contact_email: string;
  statement: string;
  status: Status;
  version: number;
  created_at: string;
  updated_at: string;
  events: StatusEvent[];
};
export type Audit = {
  id: string;
  actor_id: string;
  delegated_by: string | null;
  channel: string;
  action: string;
  data: Record<string, unknown>;
  result: string;
  at: string;
};
export type Delegation = {
  id: string;
  permissions: string[];
  application_ids: string[] | null;
  expires_at: string;
  revoked: boolean;
  expired: boolean;
};
export const statusLabel: Record<Status, string> = {
  draft: "草稿",
  submitted: "已提交",
  screening: "初筛",
};
export const formatTime = (value: string) =>
  new Date(value).toLocaleString("zh-CN", { hour12: false });
export const errorText = (error: unknown): string => {
  const e = error as { data?: { detail?: string; fields?: string[] } };
  const detail = e.data?.detail || "服务暂时不可用，请稍后重试";
  return e.data?.fields?.length
    ? `${detail}（${e.data.fields.join("、")}）`
    : detail;
};
