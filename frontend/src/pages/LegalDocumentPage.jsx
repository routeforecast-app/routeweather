import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchLegalDocument } from "../api/content";
import LoadingState from "../components/LoadingState";

function LegalDocumentPage({ defaultDocumentType = null, eyebrow = "Legal" }) {
  const { documentType } = useParams();
  const resolvedDocumentType = defaultDocumentType || documentType;
  const [document, setDocument] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadDocument() {
      try {
        setDocument(await fetchLegalDocument(resolvedDocumentType));
      } catch (loadError) {
        setError(loadError.response?.data?.detail || "Could not load this legal document.");
      } finally {
        setIsLoading(false);
      }
    }

    loadDocument();
  }, [resolvedDocumentType]);

  if (isLoading) {
    return <LoadingState label="Loading legal information..." />;
  }

  if (!document) {
    return <section className="panel empty-panel">{error || "Legal document not found."}</section>;
  }

  return (
    <section className="panel legal-document-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1>{document.title}</h1>
          <p>Last updated {new Date(document.updated_at).toLocaleString()}</p>
        </div>
        <Link className="secondary-button inline-button" to="/">
          Back to main page
        </Link>
      </div>

      <article className="legal-document-content">{document.body}</article>
    </section>
  );
}

export default LegalDocumentPage;
