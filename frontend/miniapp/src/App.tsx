import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  Clock3,
  GraduationCap,
  Headphones,
  Image as ImageIcon,
  LayoutDashboard,
  Library,
  type LucideIcon,
  MessageCircle,
  FileText,
  PlayCircle,
  ReceiptText,
  Send,
  ShieldCheck,
  ShoppingBag,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import {
  checkPayment,
  createPurchase,
  createSupportRequest,
  fetchContentFileBlob,
  fetchBlocks,
  fetchLectures,
  fetchLectureContent,
  fetchMiniAppMeta,
  fetchMyPurchases,
  fetchSections,
  fetchSupportRequests,
} from "./lib/api";
import { getTelegramUserName, hapticTap, openExternalLink } from "./lib/telegram";
import type {
  Block,
  CheckPaymentResponse,
  ContentItem,
  CreatePaymentResponse,
  Lecture,
  PurchasedLecture,
  PurchaseType,
  Section,
  SupportRequest,
  TabId,
} from "./types";

const tabs: Array<{ id: TabId; label: string; icon: LucideIcon }> = [
  { id: "catalog", label: "Каталог", icon: Library },
  { id: "purchases", label: "Покупки", icon: ShoppingBag },
  { id: "support", label: "Поддержка", icon: MessageCircle },
  { id: "admin", label: "Админ", icon: LayoutDashboard },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("catalog");
  const userName = useMemo(() => getTelegramUserName(), []);
  const metaQuery = useQuery({
    queryKey: ["miniapp-meta"],
    queryFn: fetchMiniAppMeta,
  });

  return (
    <div className="min-h-screen bg-app-bg text-app-text">
      <main className="mx-auto flex min-h-screen w-full max-w-xl flex-col pb-24">
        <header className="px-4 pb-3 pt-safe-top">
          <div className="flex items-center justify-between gap-3 py-4">
            <div>
              <p className="text-sm text-app-muted">Фармакология</p>
              <h1 className="text-2xl font-semibold tracking-normal">Здравствуйте, {userName}</h1>
            </div>
            <div
              className={
                "flex h-11 w-11 items-center justify-center rounded-lg " +
                "bg-app-accent text-white shadow-soft"
              }
            >
              <GraduationCap size={22} />
            </div>
          </div>

          <StatusStrip
            isLoading={metaQuery.isLoading}
            isError={metaQuery.isError}
            apiVersion={metaQuery.data?.api_version}
          />
        </header>

        <section className="flex-1 px-4">
          {activeTab === "catalog" && <CatalogScreen />}
          {activeTab === "purchases" && <PurchasesScreen />}
          {activeTab === "support" && <SupportScreen />}
          {activeTab === "admin" && <AdminScreen />}
        </section>

        <nav
          className={
            "fixed inset-x-0 bottom-0 border-t border-app-border " +
            "bg-app-panel px-3 pb-safe-bottom pt-2"
          }
        >
          <div className="mx-auto grid max-w-xl grid-cols-4 gap-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = tab.id === activeTab;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => {
                    hapticTap();
                    setActiveTab(tab.id);
                  }}
                  className={
                    "flex min-h-14 flex-col items-center justify-center gap-1 " +
                    "rounded-lg px-2 text-xs transition " +
                    (isActive
                      ? "bg-app-accent text-white"
                      : "text-app-muted hover:bg-app-bg hover:text-app-text"
                    )
                  }
                >
                  <Icon size={20} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </nav>
      </main>
    </div>
  );
}

function StatusStrip({
  isLoading,
  isError,
  apiVersion,
}: {
  isLoading: boolean;
  isError: boolean;
  apiVersion?: string;
}) {
  if (isLoading) {
    return <InfoLine text="Проверяем соединение с backend..." tone="neutral" />;
  }
  if (isError) {
    return <InfoLine text="Frontend открыт, backend API пока недоступен." tone="warning" />;
  }
  return <InfoLine text={`Mini App API подключен, версия ${apiVersion ?? "v1"}.`} tone="success" />;
}

function CatalogScreen() {
  const [selectedSection, setSelectedSection] = useState<Section | null>(null);
  const [selectedBlock, setSelectedBlock] = useState<Block | null>(null);
  const [activePayment, setActivePayment] = useState<CreatePaymentResponse | null>(null);
  const [paymentCheck, setPaymentCheck] = useState<CheckPaymentResponse | null>(null);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const sectionsQuery = useQuery({
    queryKey: ["catalog-sections"],
    queryFn: fetchSections,
  });
  const blocksQuery = useQuery({
    queryKey: ["catalog-blocks", selectedSection?.id],
    queryFn: () => fetchBlocks(selectedSection?.id ?? 0),
    enabled: selectedSection !== null,
  });
  const lecturesQuery = useQuery({
    queryKey: ["catalog-lectures", selectedBlock?.id],
    queryFn: () => fetchLectures(selectedBlock?.id ?? 0),
    enabled: selectedBlock !== null,
  });
  const createPurchaseMutation = useMutation({
    mutationFn: createPurchase,
    onMutate: () => {
      setPaymentError(null);
      setPaymentCheck(null);
    },
    onSuccess: (payment) => {
      hapticTap();
      setActivePayment(payment);
    },
    onError: (error) => {
      setPaymentError(getErrorText(error));
    },
  });
  const checkPaymentMutation = useMutation({
    mutationFn: checkPayment,
    onMutate: () => {
      setPaymentError(null);
      setPaymentCheck(null);
    },
    onSuccess: (result) => {
      hapticTap();
      setPaymentCheck(result);
    },
  });
  const pendingPurchaseKey =
    createPurchaseMutation.isPending && createPurchaseMutation.variables
      ? purchaseKey(
          createPurchaseMutation.variables.purchaseType,
          createPurchaseMutation.variables.objectId,
        )
      : null;

  const goBack = () => {
    hapticTap();
    if (selectedBlock) {
      setSelectedBlock(null);
      return;
    }
    setSelectedSection(null);
  };

  const handleBuy = (purchaseType: PurchaseType, objectId: number) => {
    hapticTap();
    createPurchaseMutation.mutate({ purchaseType, objectId });
  };

  return (
    <div className="space-y-4">
      <SectionTitle
        icon={BookOpen}
        title={selectedBlock?.title ?? selectedSection?.title ?? "Каталог"}
        subtitle={catalogSubtitle(selectedSection, selectedBlock)}
      />

      {(selectedSection || selectedBlock) && (
        <button
          type="button"
          onClick={goBack}
          className={
            "flex items-center gap-2 rounded-lg border border-app-border " +
            "bg-app-panel px-3 py-2 text-sm text-app-muted"
          }
        >
          <ArrowLeft size={17} />
          Назад
        </button>
      )}

      {paymentError && <InfoLine text={paymentError} tone="warning" />}

      {activePayment && (
        <PaymentPanel
          payment={activePayment}
          checkResult={paymentCheck}
          checkError={
            checkPaymentMutation.isError
              ? getErrorText(checkPaymentMutation.error)
              : null
          }
          isChecking={checkPaymentMutation.isPending}
          onOpenPayment={() => {
            if (activePayment.confirmation_url) {
              openExternalLink(activePayment.confirmation_url);
            }
          }}
          onCheckPayment={() => {
            checkPaymentMutation.mutate(activePayment.purchase.id);
          }}
          onClose={() => {
            setActivePayment(null);
            setPaymentCheck(null);
            setPaymentError(null);
          }}
        />
      )}

      {!selectedSection && (
        <CatalogList
          isLoading={sectionsQuery.isLoading}
          isError={sectionsQuery.isError}
          isEmpty={sectionsQuery.data?.length === 0}
          emptyText="В каталоге пока нет активных разделов."
        >
          {sectionsQuery.data?.map((section) => (
            <SectionCard
              key={section.id}
              section={section}
              onOpen={() => {
                hapticTap();
                setSelectedSection(section);
              }}
            />
          ))}
        </CatalogList>
      )}

      {selectedSection && !selectedBlock && (
        <CatalogList
          isLoading={blocksQuery.isLoading}
          isError={blocksQuery.isError}
          isEmpty={blocksQuery.data?.length === 0}
          emptyText="В этом разделе пока нет активных блоков."
        >
          {blocksQuery.data?.map((block) => (
            <BlockCard
              key={block.id}
              block={block}
              isBuying={pendingPurchaseKey === purchaseKey("block", block.id)}
              onOpen={() => {
                hapticTap();
                setSelectedBlock(block);
              }}
              onBuy={() => handleBuy("block", block.id)}
            />
          ))}
        </CatalogList>
      )}

      {selectedBlock && (
        <CatalogList
          isLoading={lecturesQuery.isLoading}
          isError={lecturesQuery.isError}
          isEmpty={lecturesQuery.data?.length === 0}
          emptyText="В этом блоке пока нет активных лекций."
        >
          {lecturesQuery.data?.map((lecture) => (
            <LectureCard
              key={lecture.id}
              lecture={lecture}
              isBuying={pendingPurchaseKey === purchaseKey("lecture", lecture.id)}
              onBuy={() => handleBuy("lecture", lecture.id)}
            />
          ))}
        </CatalogList>
      )}
    </div>
  );
}

function PurchasesScreen() {
  const [selectedLecture, setSelectedLecture] = useState<PurchasedLecture | null>(null);
  const [activeContent, setActiveContent] = useState<ContentItem | null>(null);
  const [filePreview, setFilePreview] = useState<{
    itemId: number;
    url: string;
  } | null>(null);
  const purchasesQuery = useQuery({
    queryKey: ["my-purchases"],
    queryFn: fetchMyPurchases,
  });
  const contentQuery = useQuery({
    queryKey: ["lecture-content", selectedLecture?.id],
    queryFn: () => fetchLectureContent(selectedLecture?.id ?? 0),
    enabled: selectedLecture !== null,
  });
  const fileMutation = useMutation({
    mutationFn: fetchContentFileBlob,
    onMutate: () => {
      setFilePreview((current) => {
        if (current) {
          URL.revokeObjectURL(current.url);
        }
        return null;
      });
    },
    onSuccess: (blob, item) => {
      setFilePreview({
        itemId: item.id,
        url: URL.createObjectURL(blob),
      });
    },
  });

  useEffect(() => {
    return () => {
      if (filePreview) {
        URL.revokeObjectURL(filePreview.url);
      }
    };
  }, [filePreview]);

  const openLecture = (lecture: PurchasedLecture) => {
    hapticTap();
    setSelectedLecture(lecture);
    setActiveContent(null);
    setFilePreview(null);
  };
  const goBack = () => {
    hapticTap();
    setSelectedLecture(null);
    setActiveContent(null);
    setFilePreview(null);
  };
  const openContent = (item: ContentItem) => {
    hapticTap();
    setActiveContent(item);
    if (item.delivery_method === "backend_file") {
      fileMutation.mutate(item);
    } else {
      setFilePreview(null);
    }
  };

  return (
    <div className="space-y-4">
      <SectionTitle
        icon={ReceiptText}
        title={selectedLecture?.title ?? "Мои покупки"}
        subtitle={
          selectedLecture
            ? "Материалы открываются только после проверки доступа."
            : "Купленные лекции и доступные материалы."
        }
      />

      {selectedLecture && (
        <button
          type="button"
          onClick={goBack}
          className={
            "flex items-center gap-2 rounded-lg border border-app-border " +
            "bg-app-panel px-3 py-2 text-sm text-app-muted"
          }
        >
          <ArrowLeft size={17} />
          Назад к покупкам
        </button>
      )}

      {!selectedLecture && (
        <CatalogList
          isLoading={purchasesQuery.isLoading}
          isError={purchasesQuery.isError}
          isEmpty={purchasesQuery.data?.length === 0}
          emptyText="У вас пока нет купленных лекций."
          errorText="Не удалось загрузить покупки. Попробуйте позже."
        >
          {purchasesQuery.data?.map((lecture) => (
            <PurchasedLectureCard
              key={lecture.id}
              lecture={lecture}
              onOpen={() => openLecture(lecture)}
            />
          ))}
        </CatalogList>
      )}

      {selectedLecture && (
        <CatalogList
          isLoading={contentQuery.isLoading}
          isError={contentQuery.isError}
          isEmpty={contentQuery.data?.content_items.length === 0}
          emptyText="Материалы для этой лекции пока не добавлены."
          errorText="Не удалось загрузить материалы лекции."
        >
          {contentQuery.data?.content_items.map((item) => (
            <MaterialRow
              key={item.id}
              item={item}
              isLoading={fileMutation.isPending && fileMutation.variables?.id === item.id}
              onOpen={() => openContent(item)}
            />
          ))}
        </CatalogList>
      )}

      {fileMutation.isError && (
        <InfoLine text={getErrorText(fileMutation.error)} tone="warning" />
      )}

      {activeContent && (
        <ContentViewer
          item={activeContent}
          fileUrl={
            filePreview?.itemId === activeContent.id ? filePreview.url : null
          }
          isLoading={
            fileMutation.isPending && fileMutation.variables?.id === activeContent.id
          }
        />
      )}
    </div>
  );
}

function SupportScreen() {
  const [message, setMessage] = useState("");
  const [sentRequest, setSentRequest] = useState<SupportRequest | null>(null);
  const supportQuery = useQuery({
    queryKey: ["support-requests"],
    queryFn: fetchSupportRequests,
  });
  const supportMutation = useMutation({
    mutationFn: createSupportRequest,
    onSuccess: async (request) => {
      hapticTap();
      setSentRequest(request);
      setMessage("");
      await supportQuery.refetch();
    },
  });
  const trimmedMessage = message.trim();
  const canSubmit = trimmedMessage.length >= 5 && !supportMutation.isPending;

  const submitSupportRequest = () => {
    if (!canSubmit) {
      return;
    }
    hapticTap();
    supportMutation.mutate(trimmedMessage);
  };

  return (
    <div className="space-y-4">
      <SectionTitle
        icon={MessageCircle}
        title="Поддержка"
        subtitle="Напишите вопрос по оплате, доступу или материалам."
      />

      <div className="rounded-lg border border-app-border bg-app-panel p-4 shadow-soft">
        <label className="text-sm font-medium" htmlFor="support-preview">
          Вопрос
        </label>
        <textarea
          id="support-preview"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          className={
            "mt-2 min-h-32 w-full resize-none rounded-lg border border-app-border " +
            "bg-app-bg p-3 text-sm outline-none focus:border-app-accent"
          }
          placeholder="Напишите вопрос по оплате, доступу или материалам"
          maxLength={4000}
          disabled={supportMutation.isPending}
        />
        <div className="mt-2 flex items-center justify-between text-xs text-app-muted">
          <span>Минимум 5 символов</span>
          <span>{message.length}/4000</span>
        </div>
        <button
          type="button"
          onClick={submitSupportRequest}
          className={
            "mt-3 flex w-full items-center justify-center gap-2 rounded-lg " +
            "bg-app-accent px-4 py-3 text-sm font-semibold " +
            "text-white disabled:opacity-70"
          }
          disabled={!canSubmit}
        >
          <Send size={17} />
          {supportMutation.isPending ? "Отправляем..." : "Отправить обращение"}
        </button>
      </div>

      {supportMutation.isError && (
        <InfoLine text={getErrorText(supportMutation.error)} tone="warning" />
      )}

      {sentRequest && (
        <InfoLine
          text={
            `Обращение #${sentRequest.id} принято. ` +
            "Администратор увидит его в Telegram и админке."
          }
          tone="success"
        />
      )}

      <div className="space-y-3">
        <h3 className="font-semibold">История обращений</h3>
        <CatalogList
          isLoading={supportQuery.isLoading}
          isError={supportQuery.isError}
          isEmpty={supportQuery.data?.length === 0}
          emptyText="История обращений пока пустая."
          errorText="Не удалось загрузить обращения."
        >
          {supportQuery.data?.map((request) => (
            <SupportRequestCard key={request.id} request={request} />
          ))}
        </CatalogList>
      </div>
    </div>
  );
}

function SupportRequestCard({ request }: { request: SupportRequest }) {
  return (
    <article className="rounded-lg border border-app-border bg-app-panel p-4 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-app-muted">
            Обращение #{request.id} от {formatDate(request.created_at)}
          </p>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-5">
            {request.message}
          </p>
        </div>
        <span
          className={
            "flex shrink-0 items-center gap-1 rounded-full px-2.5 py-1 " +
            "text-xs font-medium " +
            supportStatusClass(request.status)
          }
        >
          <Clock3 size={13} />
          {supportStatusTitle(request.status)}
        </span>
      </div>
    </article>
  );
}

function AdminScreen() {
  return (
    <div className="space-y-4">
      <SectionTitle
        icon={ShieldCheck}
        title="Админ"
        subtitle="Вкладка будет доступна только администраторам Telegram."
      />

      <div className="grid gap-3">
        <AdminQueueCard title="Новые обращения" value="0" note="Очередь поддержки" />
        <AdminQueueCard title="В работе" value="0" note="Диалоги с ответами админа" />
      </div>
    </div>
  );
}

function CatalogList({
  children,
  isLoading,
  isError,
  isEmpty,
  emptyText,
  errorText = "Не удалось загрузить каталог. Попробуйте открыть экран позже.",
}: {
  children: ReactNode;
  isLoading: boolean;
  isError: boolean;
  isEmpty: boolean;
  emptyText: string;
  errorText?: string;
}) {
  if (isLoading) {
    return (
      <div className="grid gap-3">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }
  if (isError) {
    return <InfoLine text={errorText} tone="warning" />;
  }
  if (isEmpty) {
    return <InfoLine text={emptyText} tone="neutral" />;
  }
  return <div className="grid gap-3">{children}</div>;
}

function SectionCard({ section, onOpen }: { section: Section; onOpen: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="rounded-lg border border-app-border bg-app-panel p-4 text-left shadow-soft"
    >
      <h3 className="text-lg font-semibold">{section.title}</h3>
      <p className="mt-1 text-sm leading-5 text-app-muted">
        {section.description ?? "Открыть блоки раздела"}
      </p>
    </button>
  );
}

function BlockCard({
  block,
  isBuying,
  onOpen,
  onBuy,
}: {
  block: Block;
  isBuying: boolean;
  onOpen: () => void;
  onBuy: () => void;
}) {
  return (
    <article className="rounded-lg border border-app-border bg-app-panel p-4 shadow-soft">
      <button type="button" onClick={onOpen} className="w-full text-left">
        <span
          className={
            "rounded-full bg-app-bg px-2.5 py-1 text-xs font-medium " +
            "text-app-accent-strong"
          }
        >
          Блок
        </span>
        <h3 className="mt-3 text-lg font-semibold">{block.title}</h3>
        <p className="mt-1 text-sm leading-5 text-app-muted">
          {block.description ?? "Открыть лекции блока"}
        </p>
      </button>
      <ProductAction
        price={block.price}
        owned={block.has_access}
        isLoading={isBuying}
        onBuy={onBuy}
      />
    </article>
  );
}

function LectureCard({
  lecture,
  isBuying,
  onBuy,
}: {
  lecture: Lecture;
  isBuying: boolean;
  onBuy: () => void;
}) {
  return (
    <article className="rounded-lg border border-app-border bg-app-panel p-4 shadow-soft">
      <span
        className={
          "rounded-full bg-app-bg px-2.5 py-1 text-xs font-medium " +
          "text-app-accent-strong"
        }
      >
        Лекция
      </span>
      <h3 className="mt-3 text-lg font-semibold">{lecture.title}</h3>
      <p className="mt-1 text-sm leading-5 text-app-muted">
        {lecture.short_description ?? "Описание появится позже"}
      </p>
      {lecture.full_description && (
        <p className="mt-2 text-sm leading-5 text-app-muted">
          {lecture.full_description}
        </p>
      )}
      <ProductAction
        price={lecture.price}
        owned={lecture.has_access}
        isLoading={isBuying}
        onBuy={onBuy}
      />
    </article>
  );
}

function ProductAction({
  price,
  owned,
  isLoading,
  onBuy,
}: {
  price: string;
  owned: boolean;
  isLoading: boolean;
  onBuy: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onBuy}
      className={
        "mt-4 flex w-full items-center justify-center gap-2 rounded-lg " +
        "px-4 py-3 text-sm font-semibold " +
        (owned ? "bg-app-bg text-app-accent-strong" : "bg-app-accent text-white")
      }
      disabled={owned || isLoading}
    >
      {owned ? <PlayCircle size={18} /> : <ShoppingBag size={18} />}
      {owned ? "Открыть материалы" : productActionText(price, isLoading)}
    </button>
  );
}

function PaymentPanel({
  payment,
  checkResult,
  checkError,
  isChecking,
  onOpenPayment,
  onCheckPayment,
  onClose,
}: {
  payment: CreatePaymentResponse;
  checkResult: CheckPaymentResponse | null;
  checkError: string | null;
  isChecking: boolean;
  onOpenPayment: () => void;
  onCheckPayment: () => void;
  onClose: () => void;
}) {
  const hasPaymentUrl = Boolean(payment.confirmation_url);
  const tone: "neutral" | "success" | "warning" = checkResult?.is_paid
    ? "success"
    : payment.payment_error
      ? "warning"
      : "neutral";

  return (
    <article className="rounded-lg border border-app-border bg-app-panel p-4 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-app-muted">Покупка #{payment.purchase.id}</p>
          <h3 className="mt-1 font-semibold">
            Сумма: {formatPrice(payment.purchase.price)}
          </h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg bg-app-bg px-3 py-2 text-sm text-app-muted"
        >
          Скрыть
        </button>
      </div>

      <div className="mt-3">
        <InfoLine text={paymentPanelText(payment, checkResult)} tone={tone} />
      </div>

      {checkError && (
        <div className="mt-3">
          <InfoLine text={checkError} tone="warning" />
        </div>
      )}

      <div className="mt-4 grid gap-2">
        {hasPaymentUrl && (
          <button
            type="button"
            onClick={onOpenPayment}
            className="rounded-lg bg-app-accent px-4 py-3 text-sm font-semibold text-white"
          >
            Открыть оплату
          </button>
        )}
        <button
          type="button"
          onClick={onCheckPayment}
          disabled={isChecking}
          className={
            "rounded-lg border border-app-border bg-app-bg px-4 py-3 " +
            "text-sm font-semibold text-app-accent-strong disabled:opacity-70"
          }
        >
          {isChecking ? "Проверяем..." : "Проверить оплату"}
        </button>
      </div>
    </article>
  );
}

function SectionTitle({
  icon: Icon,
  title,
  subtitle,
}: {
  icon: LucideIcon;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <div
        className={
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg " +
          "bg-app-panel text-app-accent shadow-soft"
        }
      >
        <Icon size={20} />
      </div>
      <div>
        <h2 className="text-xl font-semibold">{title}</h2>
        <p className="mt-1 text-sm leading-5 text-app-muted">{subtitle}</p>
      </div>
    </div>
  );
}

function PurchasedLectureCard({
  lecture,
  onOpen,
}: {
  lecture: PurchasedLecture;
  onOpen: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="rounded-lg border border-app-border bg-app-panel p-4 text-left shadow-soft"
    >
      <div className="flex items-start gap-3">
        <CheckCircle2 className="mt-1 shrink-0 text-app-accent" size={21} />
        <div>
          <h3 className="font-semibold">{lecture.title}</h3>
          <p className="mt-1 text-sm text-app-muted">
            Дата покупки: {formatDate(lecture.purchased_at)}
          </p>
          {lecture.short_description && (
            <p className="mt-2 text-sm leading-5 text-app-muted">
              {lecture.short_description}
            </p>
          )}
        </div>
      </div>
    </button>
  );
}

function MaterialRow({
  item,
  isLoading,
  onOpen,
}: {
  item: ContentItem;
  isLoading: boolean;
  onOpen: () => void;
}) {
  const Icon = contentIcon(item);
  return (
    <button
      type="button"
      onClick={onOpen}
      disabled={item.delivery_method === "unavailable" || isLoading}
      className={
        "flex items-center gap-3 rounded-lg border border-app-border " +
        "bg-app-panel p-4 text-left shadow-soft disabled:opacity-60"
      }
    >
      <div
        className={
          "flex h-10 w-10 items-center justify-center rounded-lg " +
          "bg-app-bg text-app-accent"
        }
      >
        <Icon size={19} />
      </div>
      <div className="min-w-0 flex-1">
        <h3 className="truncate font-medium">{item.title}</h3>
        <p className="text-sm text-app-muted">
          {isLoading ? "Загружаем..." : contentNote(item)}
        </p>
      </div>
    </button>
  );
}

function ContentViewer({
  item,
  fileUrl,
  isLoading,
}: {
  item: ContentItem;
  fileUrl: string | null;
  isLoading: boolean;
}) {
  return (
    <article className="rounded-lg border border-app-border bg-app-panel p-4 shadow-soft">
      <h3 className="font-semibold">{item.title}</h3>
      <p className="mt-1 text-sm text-app-muted">{contentNote(item)}</p>

      <div className="mt-4">
        {item.type === "text" && item.text_content && (
          <div className="whitespace-pre-wrap rounded-lg bg-app-bg p-3 text-sm leading-6">
            {item.text_content}
          </div>
        )}
        {item.type !== "text" && isLoading && (
          <InfoLine text="Загружаем материал..." tone="neutral" />
        )}
        {item.type !== "text" && !isLoading && fileUrl && (
          <FilePreview item={item} fileUrl={fileUrl} />
        )}
        {item.delivery_method === "telegram_file_id" && (
          <InfoLine
            text="Этот материал хранится в Telegram и пока открывается только через бота."
            tone="warning"
          />
        )}
      </div>
    </article>
  );
}

function FilePreview({ item, fileUrl }: { item: ContentItem; fileUrl: string }) {
  if (item.type === "pdf") {
    return (
      <iframe
        title={item.title}
        src={fileUrl}
        className="h-[520px] w-full rounded-lg border border-app-border bg-app-bg"
      />
    );
  }
  if (item.type === "image") {
    return <img src={fileUrl} alt={item.title} className="w-full rounded-lg" />;
  }
  if (item.type === "video") {
    return <video src={fileUrl} controls className="w-full rounded-lg" />;
  }
  if (item.type === "audio") {
    return <audio src={fileUrl} controls className="w-full" />;
  }
  return <InfoLine text="Формат материала пока не поддержан в Mini App." tone="warning" />;
}

function AdminQueueCard({
  title,
  value,
  note,
}: {
  title: string;
  value: string;
  note: string;
}) {
  return (
    <article className="rounded-lg border border-app-border bg-app-panel p-4 shadow-soft">
      <p className="text-sm text-app-muted">{title}</p>
      <p className="mt-2 text-3xl font-semibold">{value}</p>
      <p className="mt-1 text-sm text-app-muted">{note}</p>
    </article>
  );
}

function SkeletonCard() {
  return (
    <div className="rounded-lg border border-app-border bg-app-panel p-4 shadow-soft">
      <div className="h-4 w-24 rounded bg-app-bg" />
      <div className="mt-3 h-5 w-2/3 rounded bg-app-bg" />
      <div className="mt-2 h-4 w-full rounded bg-app-bg" />
      <div className="mt-2 h-4 w-4/5 rounded bg-app-bg" />
    </div>
  );
}

function InfoLine({ text, tone }: { text: string; tone: "neutral" | "success" | "warning" }) {
  const toneClass =
    tone === "success"
      ? "border-app-accent text-app-accent-strong"
      : "border-app-border text-app-muted";

  return (
    <div className={`rounded-lg border bg-app-panel px-3 py-2 text-sm ${toneClass}`}>
      {text}
    </div>
  );
}

function catalogSubtitle(section: Section | null, block: Block | null): string {
  if (block) {
    return block.description ?? "Выберите лекцию или купите блок целиком.";
  }
  if (section) {
    return section.description ?? "Выберите блок с лекциями.";
  }
  return "Разделы, блоки и лекции загружаются из backend API.";
}

function productActionText(price: string, isLoading: boolean): string {
  if (isLoading) {
    return "Создаем оплату...";
  }
  return `Купить за ${formatPrice(price)}`;
}

function paymentPanelText(
  payment: CreatePaymentResponse,
  checkResult: CheckPaymentResponse | null,
): string {
  if (checkResult) {
    return paymentCheckText(checkResult);
  }
  if (payment.payment_error) {
    return "Не удалось создать ссылку оплаты. Попробуйте позже или напишите в поддержку.";
  }
  if (!payment.confirmation_url) {
    return "Покупка создана, но ссылка оплаты пока недоступна.";
  }
  return "Ссылка оплаты готова. После YooKassa вернитесь сюда и проверьте оплату.";
}

function paymentCheckText(result: CheckPaymentResponse): string {
  if (result.is_paid) {
    return "Оплата подтверждена. Доступ будет доступен в разделе покупок.";
  }
  if (result.payment_status === "pending" || result.payment_status === "waiting_for_capture") {
    return "YooKassa пока не подтвердила оплату. Проверьте еще раз через несколько секунд.";
  }
  if (result.payment_status === "canceled") {
    return "Платеж отменен. Можно создать новую покупку.";
  }
  return "Платеж не прошел. Попробуйте оплатить заново.";
}

function getErrorText(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Не удалось выполнить действие. Попробуйте позже.";
}

function purchaseKey(purchaseType: PurchaseType, objectId: number): string {
  return `${purchaseType}:${objectId}`;
}

function contentIcon(item: ContentItem): LucideIcon {
  if (item.type === "audio") {
    return Headphones;
  }
  if (item.type === "image") {
    return ImageIcon;
  }
  if (item.type === "pdf" || item.type === "text") {
    return FileText;
  }
  return PlayCircle;
}

function contentNote(item: ContentItem): string {
  if (item.delivery_method === "inline_text") {
    return "Текстовый материал доступен внутри приложения.";
  }
  if (item.delivery_method === "backend_file") {
    return contentTypeTitle(item.type) + ". Доступ проверяется перед загрузкой.";
  }
  if (item.delivery_method === "telegram_file_id") {
    return "Материал хранится в Telegram и открывается через бота.";
  }
  return "Материал временно недоступен.";
}

function contentTypeTitle(type: ContentItem["type"]): string {
  return {
    pdf: "PDF",
    video: "Видео",
    audio: "Аудио",
    image: "Изображение",
    text: "Текст",
  }[type];
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("ru-RU").format(date);
}

function supportStatusTitle(status: SupportRequest["status"]): string {
  return {
    open: "Открыто",
    in_progress: "В работе",
    closed: "Закрыто",
  }[status];
}

function supportStatusClass(status: SupportRequest["status"]): string {
  return {
    open: "bg-app-bg text-app-accent-strong",
    in_progress: "bg-app-accent text-white",
    closed: "bg-app-bg text-app-muted",
  }[status];
}

function formatPrice(value: string): string {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return value;
  }
  const formatted = new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: numeric % 1 === 0 ? 0 : 2,
    minimumFractionDigits: 0,
  }).format(numeric);
  return `${formatted} ₽`;
}
