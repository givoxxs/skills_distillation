/* Bilingual label — VN lead with optional EN sub-line */

export function Bi({
  vi,
  en,
  showEn = true,
}: {
  vi: React.ReactNode;
  en?: React.ReactNode | null;
  showEn?: boolean;
}) {
  return (
    <span className="bi">
      <span className="vi">{vi}</span>
      {showEn && en && <span className="en">{en}</span>}
    </span>
  );
}
