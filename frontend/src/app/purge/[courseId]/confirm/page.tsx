import { redirect } from "next/navigation";

export default async function ConfirmRedirect({
  params,
}: {
  params: Promise<{ courseId: string }>;
}) {
  const { courseId } = await params;
  redirect(`/?course=${courseId}`);
}
