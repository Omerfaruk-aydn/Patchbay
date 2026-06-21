import React from "react";

import { cn } from "@/lib/utils";

function Input({
  className,
  type = "text",
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-md border px-3 py-2 text-sm",
        "bg-bg-elevated-2 border-border-strong text-text-primary",
        "placeholder:text-text-muted",
        "focus:outline-none focus:ring-2 focus:ring-accent-blue",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  );
}

export { Input };
