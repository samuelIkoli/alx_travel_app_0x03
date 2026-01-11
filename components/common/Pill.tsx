import React from 'react'
import { PillProps } from '@/interfaces';

export const Pill: React.FC<PillProps> = ({ label, isActive = false, onClick }) => {
return (
<button
onClick={onClick}
className={`px-4 py-2 rounded-full border transition-colors text-sm font-medium whitespace-nowrap
${isActive ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300'}
`}
>
{label}
</button>
);
};


// Filter Section Component
const filters = [
'Top Villa',
'Self Checkin',
'Beachfront',
'Mountain View',
'Private Pool',
'Pet Friendly',
'Luxury',
];


export const FilterSection: React.FC = () => {
const [activeFilter, setActiveFilter] = React.useState<string>('');


return (
<div className="flex flex-wrap gap-3 py-4">
{filters.map((filter) => (
<Pill
key={filter}
label={filter}
isActive={activeFilter === filter}
onClick={() => setActiveFilter(filter)}
/>
))}
</div>
);
};