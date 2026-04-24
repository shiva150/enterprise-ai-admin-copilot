import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { ChatPane } from "./components/ChatPane";
import { ContextPanel } from "./components/ContextPanel";

export default function App() {
  return (
    <div className="bg-background text-on-background min-h-screen flex overflow-hidden">
      <Sidebar />
      <main className="flex-1 md:ml-[260px] h-screen flex flex-col pt-16 md:pt-0 bg-surface">
        <TopBar />
        <div className="flex-1 flex overflow-hidden">
          <ChatPane />
          <ContextPanel />
        </div>
      </main>
    </div>
  );
}
