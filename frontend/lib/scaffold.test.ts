import { describe, expect, it } from "vitest";

import { SCAFFOLD_STATUS } from "./scaffold";

describe("scaffold", () => {
  it("exposes the scaffold status", () => {
    expect(SCAFFOLD_STATUS).toBe("application scaffold only");
  });
});
