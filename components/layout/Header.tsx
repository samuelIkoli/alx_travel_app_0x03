import React from "react";
import { Search } from "lucide-react";
import Button from "@/components/common/Button";

const accommodationTypes = [
  "Rooms",
  "Mansion",
  "Countryside",
  "Beachfront",
  "Villa",
  "Cabin",
  "Penthouse",
];

export default function Header() {
  return (
    <header className="w-full shadow-sm bg-white px-6 py-4 flex flex-col gap-4">
      {/* Top Section */}
      <div className="flex items-center justify-between">
        {/* Logo */}
        <h1 className="text-2xl font-semibold">StayScape</h1>

        {/* Search Bar */}
        <div className="flex items-center gap-2 border rounded-full px-4 py-2 w-[350px]">
          <Search className="w-5 h-5 opacity-60" />
          <input
            type="text"
            placeholder="Search destinations, villas, cabins..."
            className="outline-none w-full text-sm"
          />
        </div>

        {/* Auth Buttons */}
        <div className="flex items-center gap-3">
          <Button variant="ghost" className="rounded-full px-5 py-2">
            Sign In
          </Button>
          <Button className="rounded-full px-5 py-2">Sign Up</Button>
        </div>
      </div>

      {/* Accommodation Types */}
      <nav className="flex items-center gap-6 overflow-x-auto pb-2">
        {accommodationTypes.map((type) => (
          <button
            key={type}
            className="text-sm opacity-70 hover:opacity-100 transition font-medium"
          >
            {type}
          </button>
        ))}
      </nav>
    </header>
  );
}
