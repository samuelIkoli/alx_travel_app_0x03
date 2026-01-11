import React from "react";
import Image from "next/image";
import { HERO_BG, PROPERTYLISTINGSAMPLE, PropertyProps } from "@/constants/constants";

const PropertyCard: React.FC<{ property: PropertyProps }> = ({ property }) => {
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden w-full md:w-[300px]">
      <div className="relative h-48 w-full">
        <Image
          src={property.image}
          alt={property.name}
          fill
          className="object-cover"
        />
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-lg mb-1">{property.name}</h3>
        <p className="text-gray-600 mb-2">${property.price} / night</p>
        <p className="text-yellow-500 font-medium">⭐ {property.rating}</p>
      </div>
    </div>
  );
};

export default function HomePage() {
  return (
    <div>
      {/* Hero Section */}
      <section className="relative w-full h-[80vh] flex items-center justify-center text-center text-white">
        <Image
          src={HERO_BG}
          alt="Hero Background"
          fill
          className="object-cover brightness-75"
          priority
        />

        <div className="relative z-10 max-w-2xl px-4">
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            Find your favorite place here!
          </h1>
          <p className="text-lg md:text-xl opacity-90">
            The best prices for over 2 million properties worldwide.
          </p>
        </div>
      </section>

      {/* Listing Section */}
      <section className="py-8 px-4 md:px-8">
        <h2 className="text-2xl font-bold mb-6">Featured Properties</h2>
        <div className="flex flex-wrap gap-6 justify-center">
          {PROPERTYLISTINGSAMPLE.map((property) => (
            <PropertyCard key={property.name} property={property} />
          ))}
        </div>
      </section>
    </div>
  );
}