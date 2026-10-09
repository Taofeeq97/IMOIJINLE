import { redirect } from "next/navigation";

/** Public catalog is cohorts (academic sessions), not programs. */
export default function ProgramsPublicRedirectPage() {
  redirect("/cohorts");
}
