import Link from "next/link";

export function FaqLink() {
  return (
    <Link
      href="/faq"
      className="block w-full rounded-lg border-2 border-slate-300 bg-white px-6 py-4 text-center text-base font-semibold text-slate-900 shadow-sm transition hover:border-slate-400 hover:bg-slate-50"
    >
      FAQ
    </Link>
  );
}
