import { ReviewDetailView } from "@/features/idp/ReviewDetailView";

export default async function ReviewDetailPage({ params }: { params: Promise<{ documentId: string }> }) {
  const { documentId } = await params;
  return <ReviewDetailView documentId={documentId} />;
}
