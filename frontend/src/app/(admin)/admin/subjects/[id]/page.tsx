import { redirect } from "next/navigation";

export default async function SubjectDetailRedirect({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/admin/subjects/${id}/manage/curriculum`);
}
