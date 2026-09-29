import { describe, it, expect } from "vitest";
import { hashPassword, verifyPassword } from "../password";

describe("password hashing (argon2id)", () => {
  it("produces an argon2id hash with the specified parameters", async () => {
    const hash = await hashPassword("correct-horse-battery-staple");
    expect(hash).toMatch(/^\$argon2id\$/);
    expect(hash).toMatch(/m=65536/);
    expect(hash).toMatch(/t=3/);
  });

  it("verifies the correct password as true", async () => {
    const hash = await hashPassword("my-real-password-123");
    expect(await verifyPassword(hash, "my-real-password-123")).toBe(true);
  });

  it("rejects an incorrect password", async () => {
    const hash = await hashPassword("my-real-password-123");
    expect(await verifyPassword(hash, "wrong-password")).toBe(false);
  });

  it("produces a different hash for the same password each time (unique salt)", async () => {
    const hash1 = await hashPassword("same-password");
    const hash2 = await hashPassword("same-password");
    expect(hash1).not.toBe(hash2);
    expect(await verifyPassword(hash1, "same-password")).toBe(true);
    expect(await verifyPassword(hash2, "same-password")).toBe(true);
  });

  it("returns false (not a throw) for a malformed hash string", async () => {
    await expect(verifyPassword("not-a-real-hash", "anything")).resolves.toBe(false);
  });

  it("is case-sensitive and whitespace-sensitive", async () => {
    const hash = await hashPassword("Password123");
    expect(await verifyPassword(hash, "password123")).toBe(false);
    expect(await verifyPassword(hash, "Password123 ")).toBe(false);
  });
});
