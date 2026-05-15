import { TopBar } from "@/components/topbar";
import { RunClient } from "./run-client";

export default function RunPage() {
  return (
    <>
      <TopBar
        crumbs={[
          { label: "Tổng quan", href: "/" },
          { label: "Live run · Chạy thử" },
        ]}
      />
      <RunClient bilingual={true} />
    </>
  );
}
