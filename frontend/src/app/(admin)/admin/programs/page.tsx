import { redirect } from "next/navigation";

/** Programs were removed from the product model. Cohort is the root (academic session). */
export default function ProgramsRedirectPage() {
  redirect("/admin/cohorts");
}
