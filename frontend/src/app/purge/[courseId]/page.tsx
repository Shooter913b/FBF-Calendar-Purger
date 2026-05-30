import { redirect } from "next/navigation";

export default async function PurgeRedirect({
  params,
}: {
  params: Promise<{ courseId: string }>;
}) {
  const { courseId } = await params;
  redirect(`/?course=${courseId}`);
}
