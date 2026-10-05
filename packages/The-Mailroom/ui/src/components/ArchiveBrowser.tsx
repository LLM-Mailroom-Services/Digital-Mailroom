import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { archiveApi } from '@/api/archive'
import { documentsApi } from '@/api/documents'
import { FileText, Download, ShieldCheck, Search } from 'lucide-react'

export default function ArchiveBrowser() {
  const [selectedMatter, setSelectedMatter] = useState('')
  const [selectedType, setSelectedType] = useState('')
  const [search, setSearch] = useState('')

  const { data: matters } = useQuery({
    queryKey: ['matters'],
    queryFn: documentsApi.listMatters,
  })

  const { data: entries, isLoading, error } = useQuery({
    queryKey: ['archive', selectedMatter, selectedType],
    queryFn: () => archiveApi.list({
      matter_id: selectedMatter || undefined,
      doc_type: selectedType || undefined,
    }),
  })

  const filtered = entries?.filter((entry) =>
    entry.doc_id.toLowerCase().includes(search.toLowerCase())
    || entry.doc_type.toLowerCase().includes(search.toLowerCase()),
  )

  const handleDownload = async (docId: string) => {
    const blob = await archiveApi.download(docId)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = docId
    a.click()
    window.URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Archive Browser</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Local operator `archive_index` — never a fabricated catalog.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search documents…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-3 py-2 rounded-md border border-input bg-background text-sm w-64"
          />
        </div>
        <select
          value={selectedMatter}
          onChange={(e) => setSelectedMatter(e.target.value)}
          className="px-3 py-2 rounded-md border border-input bg-background text-sm"
        >
          <option value="">All matters</option>
          {matters?.map((matter) => (
            <option key={matter.matter_id} value={matter.matter_id}>{matter.matter_id}</option>
          ))}
        </select>
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="px-3 py-2 rounded-md border border-input bg-background text-sm"
        >
          <option value="">All types</option>
          <option value="contract">Contract</option>
          <option value="corporate_record">Corporate Record</option>
          <option value="correspondence">Correspondence</option>
          <option value="compliance_filing">Compliance Filing</option>
          <option value="insurance_claim">Insurance Claim</option>
        </select>
      </div>

      {error && (
        <p className="text-sm text-destructive">Archive list requires a signed-in operator token.</p>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading archive…</div>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="text-left px-4 py-3 font-medium">Document</th>
                <th className="text-left px-4 py-3 font-medium">Type</th>
                <th className="text-left px-4 py-3 font-medium">Matter</th>
                <th className="text-left px-4 py-3 font-medium">Size</th>
                <th className="text-left px-4 py-3 font-medium">Archived</th>
                <th className="text-right px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered?.map((entry) => (
                <tr key={entry.doc_id} className="hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{entry.doc_id}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{entry.doc_type}</td>
                  <td className="px-4 py-3 text-muted-foreground">{entry.matter_id}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {entry.file_size_bytes ? `${(entry.file_size_bytes / 1024).toFixed(1)} KB` : '—'}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {entry.archived_at ? new Date(entry.archived_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => void handleDownload(entry.doc_id)}
                        className="p-1.5 rounded-md hover:bg-muted"
                        title="Download"
                      >
                        <Download className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => void archiveApi.verify(entry.doc_id).then((r) => {
                          window.alert(r.valid ? 'Checksum valid' : 'Checksum mismatch')
                        })}
                        className="p-1.5 rounded-md hover:bg-muted"
                        title="Verify checksum"
                      >
                        <ShieldCheck className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {(!filtered || filtered.length === 0) && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-muted-foreground">
                    No archived documents in the operator index
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
