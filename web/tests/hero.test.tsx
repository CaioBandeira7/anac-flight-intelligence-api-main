import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GetStartedButton } from "@/components/landing/get-started-button";

describe("GetStartedButton", () => {
  it("is a keyboard-accessible button that launches once activated", async () => {
    const onLaunch = vi.fn();
    render(<GetStartedButton onLaunch={onLaunch} />);
    const btn = screen.getByRole("button", { name: /get started/i });
    btn.focus();
    expect(btn).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(onLaunch).toHaveBeenCalledTimes(1);
  });

  it("can be disabled while the takeoff runs", () => {
    render(<GetStartedButton onLaunch={() => {}} disabled />);
    expect(screen.getByRole("button", { name: /get started/i })).toBeDisabled();
  });
});
