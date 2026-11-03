import { CalendarView } from "@/features/execution/CalendarView";
import { MeetingsTabs } from "@/features/execution/MeetingsTabs";

/** SCR `/meetings/calendar` (M3.1): the caller's personal calendar + task deadlines (EP-CAL). */
export default function CalendarPage() {
  return (
    <div className="flex flex-col gap-4">
      <MeetingsTabs active="calendar" />
      <CalendarView />
    </div>
  );
}
