import React from 'react';
import { Search } from 'lucide-react';

export interface SearchInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  containerClassName?: string;
}

export const SearchInput: React.FC<SearchInputProps> = ({ containerClassName = '', className = '', ...props }) => (
  <label className={`search-input-field ${containerClassName}`}>
    <Search size={16} />
    <input className={className} {...props} />
  </label>
);

export default SearchInput;
