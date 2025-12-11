import { NextResponse } from 'next/server';
import { auth } from "@/auth";
import { getUserCredits } from "@/services/credit";

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  try {
    const session = await auth();
    if (!session?.user?.uuid) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userId = session.user.uuid;
    const userCredits = await getUserCredits(userId);

    return NextResponse.json({ 
        balance: userCredits.left_credits 
    });

  } catch (error: any) {
    console.error('Fetch balance failed:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}