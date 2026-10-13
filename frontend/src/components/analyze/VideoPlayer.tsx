import { embedUrl } from '../../utils/youtube'

interface Props {
  videoId: string
  title?: string
}

export default function VideoPlayer({ videoId, title = 'Recipe video' }: Props) {
  return (
    <div className="relative w-full" style={{ paddingBottom: '56.25%' /* 16:9 */ }}>
      <iframe
        className="absolute inset-0 w-full h-full rounded-xl border border-slate-200 shadow-sm"
        src={embedUrl(videoId)}
        title={title}
        allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowFullScreen
        loading="lazy"
      />
    </div>
  )
}
