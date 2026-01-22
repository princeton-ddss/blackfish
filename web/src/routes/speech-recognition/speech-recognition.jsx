import { useEffect, useMemo, useState } from "react";

import { Page } from "@/components/Page";
import { TaskContainer } from "@/components/TaskContainer";
import { SidebarContainer } from "@/components/SidebarContainer";

import SpeechRecognitionContainer from "./components/SpeechRecognitionContainer";
import SpeechRecognitionContainerOptionsForm from "./components/SpeechRecognitionContainerOptionsForm";
import SpeechRecognitionParametersForm from "./components/SpeechRecognitionParametersForm";

export default function SpeechRecognitionPage() {
  const [parameters, setParameters] = useState({
    language: {
      id: 0,
      name: "English",
    },
  });

  const defaultContainerOptions = useMemo(() => {
    return {
      input_dir: "",
    };
  }, []);

  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setIsReady(true);
  }, []);

  if (!isReady) return null;

  return (
    <Page task="speech-recognition">
      <TaskContainer>
        {/* note that this is "TextGenerationTask" on the text generation page */}
        <SpeechRecognitionContainer parameters={parameters} />
      </TaskContainer>

      <SidebarContainer
        task="speech-recognition"
        defaultContainerOptions={defaultContainerOptions}
        ContainerOptionsFormComponent={SpeechRecognitionContainerOptionsForm}
      >
        <SpeechRecognitionParametersForm
          parameters={parameters}
          setParameters={setParameters}
        />
      </SidebarContainer>
    </Page>
  );
}
