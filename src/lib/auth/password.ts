import argon2, { type HashOptions } from "argon2";

/**
 * OWASP 2026 Password Storage Cheat Sheet recommendation for Argon2id,
 * interactive single-verification login (researched, not guessed — see
 * conversation): time cost 3, memory cost 64 MiB, parallelism 1.
 * argon2's own npm default (m=65536 KiB=64MiB, p=4, t=3) is close; p is
 * set explicitly here to match the specific cited recommendation rather
 * than leave it at the library's default.
 */
const ARGON2_OPTIONS: HashOptions = {
  type: argon2.argon2id,
  memoryCost: 65536, // 64 MiB, in KiB
  timeCost: 3,
  parallelism: 1,
};

export async function hashPassword(plainPassword: string): Promise<string> {
  return argon2.hash(plainPassword, ARGON2_OPTIONS);
}

export async function verifyPassword(hash: string, plainPassword: string): Promise<boolean> {
  try {
    return await argon2.verify(hash, plainPassword);
  } catch {
    // argon2.verify throws on a malformed/foreign hash string rather than
    // returning false — treated as "not a match" here, not an error the
    // caller needs to handle separately (a bad hash should never
    // authenticate someone, whatever the reason it's bad).
    return false;
  }
}
