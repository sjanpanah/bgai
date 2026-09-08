// Baked in at build time: CI passes the deployed SHA, and vite.config falls back
// to the working tree so a local build still identifies itself rather than
// claiming to be "unknown".
const commit = import.meta.env.VITE_COMMIT ?? "unknown";

const DIRTY = "-dirty";

// A local build on top of uncommitted edits is marked dirty; abbreviating must
// keep that marker, since it's the part that says "this isn't really a commit".
function shorten(value: string): string {
  return value.endsWith(DIRTY)
    ? value.slice(0, -DIRTY.length).slice(0, 7) + DIRTY
    : value.slice(0, 7);
}

export const FRONTEND_COMMIT = commit;
export const FRONTEND_SHORT = shorten(commit);
