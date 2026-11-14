import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, vi, type MockInstance } from "vitest";
import { cleanup } from "@testing-library/react";

/**
 * React `act(...)` warnings are a signal that a test asserted while a state
 * update was still pending — the classic source of flaky, meaningless tests.
 *
 * P1 review flagged one such warning on the loading-state test. It was fixed by
 * making that test deterministic (a request that never settles) and by awaiting
 * the rejection in the sibling test — not by muting console output.
 *
 * To stop the warning silently coming back, `console.error` is *observed* here
 * and any `act(...)` message fails the test. Nothing is filtered or suppressed:
 * `vi.spyOn` without a mock implementation still calls through to the original,
 * so every message reaches the console exactly as React emitted it.
 */
const ACT_WARNING = /not wrapped in act\(/;

let consoleErrorSpy: MockInstance | undefined;

beforeEach(() => {
  consoleErrorSpy = vi.spyOn(console, "error");
});

afterEach(() => {
  const messages = (consoleErrorSpy?.mock.calls ?? []).map((args: unknown[]) =>
    args.map((value) => String(value)).join(" "),
  );
  consoleErrorSpy?.mockRestore();
  consoleErrorSpy = undefined;
  cleanup();

  const actWarnings = messages.filter((text) => ACT_WARNING.test(text));
  if (actWarnings.length > 0) {
    throw new Error(
      `React reported ${actWarnings.length} unwrapped state update(s) (act(...)).\n` +
        "Fix the test so the update is flushed inside act(); do not suppress the warning.\n\n" +
        actWarnings.join("\n---\n"),
    );
  }
});
