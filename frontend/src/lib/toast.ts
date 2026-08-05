import { toast } from "sonner";

export function toastError(message: string) {
  toast.error(message);
}

export function toastSuccess(message: string) {
  toast.success(message);
}

export function toastInfo(message: string) {
  toast.info(message);
}
