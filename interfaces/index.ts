export interface PillProps {
  label: string;
  isActive?: boolean;
  onClick?: () => void;
}


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
  discount: string;   // if empty string, it's still valid
}
