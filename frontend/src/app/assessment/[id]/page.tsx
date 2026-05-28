"use client";

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

export default function AssessmentCockpitRedirect() {
  const { id } = useParams();
  const router = useRouter();
  
  useEffect(() => {
    router.push(`/patient/${id}/reports`);
  }, [id, router]);

  return (
    <div className="min-h-screen flex items-center justify-center clinical-gradient">
      <div className="w-8 h-8 border-2 border-neon-blue border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
