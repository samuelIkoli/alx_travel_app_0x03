export const HERO_BG = "/images/hero.jpg";

export interface AddressProps {
state: string;
city: string;
country: string;
}


export interface OfferProps {
bed: string;
shower: string;
occupants: string;
}


export interface PropertyProps {
name: string;
address: AddressProps;
rating: number;
category: string[];
price: number;
offers: OfferProps;
image: string;
discount: string;
}

export const PROPERTYLISTINGSAMPLE: PropertyProps[] = [
{
name: "Villa Ocean Breeze",
address: { state: "Seminyak", city: "Bali", country: "Indonesia" },
rating: 4.89,
category: ["Luxury Villa", "Pool", "Free Parking"],
price: 3200,
offers: { bed: "3", shower: "3", occupants: "4-6" },
image: "/images/property1.jpg",
discount: ""
},
{
name: "Mountain Escape Chalet",
address: { state: "Aspen", city: "Colorado", country: "USA" },
rating: 4.7,
category: ["Mountain View", "Fireplace", "Self Checkin"],
price: 1800,
offers: { bed: "4", shower: "2", occupants: "5-7" },
image: "/images/property2.jpg",
discount: "30"
},
{
name: "Cozy Desert Retreat",
address: { state: "Palm Springs", city: "California", country: "USA" },
rating: 4.92,
category: ["Desert View", "Pet Friendly", "Self Checkin"],
price: 1500,
offers: { bed: "2", shower: "1", occupants: "2-3" },
image: "/images/property3.jpg",
discount: ""
}
];