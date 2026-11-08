import { SCAFFOLD_STATUS } from "@/lib/scaffold";

export default function Home() {
  return (
    <main>
      <h1>NEXUS AI</h1>
      <p>Local-first logistics assistant.</p>
      <p>Status: {SCAFFOLD_STATUS}</p>
    </main>
  );
}
