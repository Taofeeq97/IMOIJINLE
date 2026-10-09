import { redirect } from "next/navigation";

/** Legacy Program detail — product root is Cohort now. */
export default function ProgramDetailRedirectPage() {
  redirect("/admin/cohorts");
}
