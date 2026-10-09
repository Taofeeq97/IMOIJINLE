import { PageHeader } from "@/components/shared/page-header";

export default async function CmsPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <PageHeader title={slug} description="CMS page stub." />;
}
