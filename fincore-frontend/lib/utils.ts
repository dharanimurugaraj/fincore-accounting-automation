import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(amount);
}

export function formatCrores(amount: number): string {
  return (amount / 1e7).toFixed(2);
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}
