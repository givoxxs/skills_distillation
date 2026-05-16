import { Bi } from "@/components/bi";
import { TopBar } from "@/components/topbar";
import { RunClient } from "./run-client";

export default function RunPage() {
  return (
    <>
      <TopBar
        crumbs={[
          { label: <Bi vi="Tổng quan" en="Overview" />, href: "/" },
          { label: <Bi vi="Chạy thử" en="Live run" /> },
        ]}
      />
      <RunClient bilingual={true} />
    </>
  );
}
