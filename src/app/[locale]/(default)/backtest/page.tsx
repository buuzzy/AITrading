import { auth } from "@/auth";
import { getUserCredits } from "@/services/credit";
import BacktestClient from "./BacktestClient";

export const dynamic = 'force-dynamic';

export default async function BacktestPage() {
  const session = await auth();
  let credits: number | null = null;

  if (session?.user?.uuid) {
      try {
          const userCredits = await getUserCredits(session.user.uuid);
          credits = userCredits.left_credits;
      } catch (e) {
          console.error('Failed to fetch credits on server', e);
      }
  }

  return <BacktestClient initialCredits={credits} />;
}
