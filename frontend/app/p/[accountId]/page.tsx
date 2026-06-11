import { redirect } from "next/navigation";

export default async function PublicPlayerPage({
  params,
}: {
  params: Promise<{ accountId: string }>;
}) {
  const { accountId } = await params;
  redirect(`/?player=${encodeURIComponent(accountId)}`);
}
