"use client";

import {
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
  Label,
} from "@headlessui/react";
import { ChevronUpDownIcon, CheckIcon } from "@heroicons/react/20/solid";
import PropTypes from "prop-types";

const languages = [
  { id: 1, name: "English" },
  { id: 2, name: "French" },
  { id: 3, name: "Spanish" },
  { id: 4, name: "German" },
  { id: 5, name: "Chinese" },
  { id: 6, name: "Norwegian" },
  { id: 7, name: "Swedish" },
  { id: 8, name: "Dutch" },
];

function LanguageSelect({ language, setLanguage }) {
  return (
    <Listbox value={language} onChange={setLanguage}>
      <Label className="mt-4 block text-sm font-medium leading-6 text-gray-900">
        Language
      </Label>
      <div className="relative mt-2">
        <ListboxButton className="relative w-full cursor-default rounded-md bg-white py-1.5 pl-3 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm sm:leading-6">
          <span className="block truncate">{language.name}</span>
          <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
            <ChevronUpDownIcon
              aria-hidden="true"
              className="h-5 w-5 text-gray-400"
            />
          </span>
        </ListboxButton>

        <ListboxOptions
          transition
          className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none data-[closed]:data-[leave]:opacity-0 data-[leave]:transition data-[leave]:duration-100 data-[leave]:ease-in sm:text-sm"
        >
          {languages.map((person) => (
            <ListboxOption
              key={person.id}
              value={person}
              className="group relative cursor-default select-none py-2 pl-3 pr-9 text-gray-900 data-[focus]:bg-blue-500 data-[focus]:text-white"
            >
              <span className="block truncate font-normal group-data-[selected]:font-semibold">
                {person.name}
              </span>

              <span className="absolute inset-y-0 right-0 flex items-center pr-4 text-blue-500 group-data-[focus]:text-white [.group:not([data-selected])_&]:hidden">
                <CheckIcon aria-hidden="true" className="h-5 w-5" />
              </span>
            </ListboxOption>
          ))}
        </ListboxOptions>
      </div>
    </Listbox>
  );
}

LanguageSelect.propTypes = {
  language: PropTypes.string,
  setLanguage: PropTypes.func,
};

function SpeechRecognitionParametersForm({parameters, setParameters}) {

  const setLanguage = (language) => {
    setParameters({
      ...parameters,
      language: language,
    });
  };
  return (
    <LanguageSelect language={parameters.language} setLanguage={setLanguage} />
  );
}

SpeechRecognitionParametersForm.propTypes = {
  parameters: PropTypes.object,
  setParameters: PropTypes.func,
};

export default SpeechRecognitionParametersForm;
