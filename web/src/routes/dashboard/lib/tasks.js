import {
  ChatBubbleBottomCenterTextIcon,
  SpeakerWaveIcon,
  PhotoIcon,
} from "@heroicons/react/24/outline";

const tasks = [
  {
    id: "text-generation",
    name: "Text Generation",
    description: "Generate text based on a prompt.",
    icon: ChatBubbleBottomCenterTextIcon,
    path: "text-generation",
  },
  {
    id: "speech-recognition",
    name: "Speech Recognition",
    description: "Convert spoken words to text.",
    icon: SpeakerWaveIcon,
    path: "speech-recognition",
  },
  {
    id: "object-detection",
    name: "Object Detection",
    description: "Locate and classify objects in images.",
    icon: PhotoIcon,
    path: "object-detection",
  },
];

export default tasks;
