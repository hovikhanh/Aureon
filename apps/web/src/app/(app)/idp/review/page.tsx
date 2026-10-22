import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { ReviewQueueView } from "@/features/idp/ReviewQueueView";

export default async function ReviewQueuePage() {
  const session = await getServerSession(authOptions);
  return <ReviewQueueView userId={session?.user.id ?? ""} />;
}
