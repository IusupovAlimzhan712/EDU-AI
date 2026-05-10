import { AppSidebar } from '../components/AppSidebar';
import { CircularProgress } from '../components/CircularProgress';
import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Check, AlertTriangle } from 'lucide-react';

interface EssayFeedbackProps {
  onNavigate: (page: any, params?: any) => void;
  essayId: string | null;
}

export function EssayFeedback({ onNavigate, essayId }: EssayFeedbackProps) {
  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="essay-practice" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <h1 className="text-2xl font-bold text-[#111827]">Essay Feedback</h1>
          <p className="text-[#6B7280]">Huraikan faktor-faktor kejatuhan Kesultanan Melayu Melaka</p>
        </div>

        {/* Main Content */}
        <div className="p-8 max-w-5xl mx-auto">
          {/* Score Header */}
          <div className="bg-white rounded-xl shadow-edu-md p-8 mb-8">
            <div className="flex items-center gap-8">
              <CircularProgress percentage={70} size="large" />

              <div className="flex-1">
                <h2 className="text-3xl font-bold text-[#111827] mb-4">7/10</h2>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-[#6B7280] mb-1">Content Accuracy</p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
                        <div className="h-full bg-[#1E3A8A] rounded-full" style={{ width: '80%' }} />
                      </div>
                      <span className="text-sm font-bold text-[#111827]">3/4</span>
                    </div>
                  </div>

                  <div>
                    <p className="text-sm text-[#6B7280] mb-1">Structure & Organization</p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
                        <div className="h-full bg-[#1E3A8A] rounded-full" style={{ width: '100%' }} />
                      </div>
                      <span className="text-sm font-bold text-[#111827]">2/2</span>
                    </div>
                  </div>

                  <div>
                    <p className="text-sm text-[#6B7280] mb-1">Analysis & Understanding</p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
                        <div className="h-full bg-[#1E3A8A] rounded-full" style={{ width: '50%' }} />
                      </div>
                      <span className="text-sm font-bold text-[#111827]">1.5/3</span>
                    </div>
                  </div>

                  <div>
                    <p className="text-sm text-[#6B7280] mb-1">Language & Expression</p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
                        <div className="h-full bg-[#1E3A8A] rounded-full" style={{ width: '50%' }} />
                      </div>
                      <span className="text-sm font-bold text-[#111827]">0.5/1</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="feedback" className="mb-8">
            <TabsList className="bg-white border border-[#E5E7EB] mb-6">
              <TabsTrigger value="response">Your Response</TabsTrigger>
              <TabsTrigger value="feedback">AI Feedback</TabsTrigger>
              <TabsTrigger value="model">Model Answer</TabsTrigger>
            </TabsList>

            <TabsContent value="response">
              <div className="bg-white rounded-xl shadow-edu-sm p-6">
                <p className="text-[#111827] leading-relaxed whitespace-pre-line">
                  Kejatuhan Kesultanan Melayu Melaka pada tahun 1511 adalah hasil daripada pelbagai faktor dalaman dan luaran. Faktor pertama ialah persaingan perdagangan dengan kuasa Eropah, terutamanya Portugis yang ingin menguasai perdagangan rempah. Kedua, kelemahan pertahanan Melaka kerana konflik dalaman dalam kerajaan. Ketiga, pengkhianatan oleh beberapa pembesar dan pedagang tempatan yang bekerjasama dengan Portugis. Keempat, kekurangan persediaan ketenteraan Melaka berbanding dengan senjata moden Portugis. Kelima, masalah ekonomi akibat monopoli perdagangan yang semakin terancam.
                </p>
              </div>
            </TabsContent>

            <TabsContent value="feedback">
              <div className="space-y-6">
                {/* Strengths */}
                <div className="bg-white rounded-xl shadow-edu-sm p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-8 h-8 bg-[#D1FAE5] rounded-full flex items-center justify-center">
                      <Check className="w-5 h-5 text-[#059669]" />
                    </div>
                    <h3 className="text-lg font-bold text-[#111827]">Strengths</h3>
                  </div>
                  <ul className="space-y-3 text-[#374151]">
                    <li className="flex gap-3">
                      <span className="text-[#059669] font-bold">•</span>
                      <span>Well-structured response with clear introduction and five distinct factors</span>
                    </li>
                    <li className="flex gap-3">
                      <span className="text-[#059669] font-bold">•</span>
                      <span>Mentioned the year 1511 correctly</span>
                    </li>
                    <li className="flex gap-3">
                      <span className="text-[#059669] font-bold">•</span>
                      <span>Identified both internal and external factors contributing to the fall</span>
                    </li>
                  </ul>
                </div>

                {/* Areas for Improvement */}
                <div className="bg-white rounded-xl shadow-edu-sm p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-8 h-8 bg-[#FEF3C7] rounded-full flex items-center justify-center">
                      <AlertTriangle className="w-5 h-5 text-[#F59E0B]" />
                    </div>
                    <h3 className="text-lg font-bold text-[#111827]">Areas for Improvement</h3>
                  </div>
                  <ul className="space-y-3 text-[#374151]">
                    <li className="flex gap-3">
                      <span className="text-[#F59E0B] font-bold">•</span>
                      <span>Provide more specific historical details - mention Alfonso de Albuquerque by name</span>
                    </li>
                    <li className="flex gap-3">
                      <span className="text-[#F59E0B] font-bold">•</span>
                      <span>Elaborate on the role of Sultan Mahmud Shah during this period</span>
                    </li>
                    <li className="flex gap-3">
                      <span className="text-[#F59E0B] font-bold">•</span>
                      <span>Include the impact of the fall on the regional trade network</span>
                    </li>
                  </ul>
                </div>

                {/* Detailed Feedback */}
                <div className="bg-white rounded-xl shadow-edu-sm p-6">
                  <h3 className="text-lg font-bold text-[#111827] mb-4">Detailed Feedback</h3>
                  <p className="text-[#374151] leading-relaxed">
                    Your essay demonstrates a good understanding of the factors leading to the fall of Melaka. However, to achieve full marks, you should provide more specific historical evidence. For example, when discussing Portuguese involvement, mention specific leaders like Alfonso de Albuquerque and the date of the attack (August 1511). Additionally, elaborate on how internal conflicts, such as disputes between nobles, weakened the sultanate's ability to defend itself.
                  </p>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="model">
              <div className="bg-white rounded-xl shadow-edu-sm p-6">
                <div className="bg-[#EFF6FF] border-l-4 border-[#1E3A8A] p-4 rounded mb-4">
                  <p className="text-sm text-[#1E3A8A] font-medium">
                    This is a model answer demonstrating full marks criteria
                  </p>
                </div>
                <p className="text-[#111827] leading-relaxed whitespace-pre-line">
                  Kejatuhan Kesultanan Melayu Melaka kepada Portugis pada 24 Ogos 1511 merupakan peristiwa penting dalam sejarah Alam Melayu. Beberapa faktor utama menyumbang kepada kejatuhan ini:

                  Pertama, persaingan perdagangan yang sengit dengan kuasa Eropah, khususnya Portugis di bawah pimpinan Alfonso de Albuquerque yang ingin menguasai perdagangan rempah di Nusantara.

                  Kedua, kelemahan pertahanan Melaka akibat konflik dalaman antara pembesar negara, terutamanya perselisihan faham mengenai polisi perdagangan dengan pedagang asing.

                  Ketiga, pengkhianatan oleh beberapa pedagang tempatan dan pembesar yang bekerjasama dengan Portugis atas kepentingan peribadi mereka dalam perdagangan.

                  Keempat, ketidakseimbangan kuasa ketenteraan di mana Portugis memiliki senjata api moden dan meriam yang lebih canggih berbanding senjata tradisional Melaka.

                  Kelima, masalah ekonomi yang melanda Melaka akibat monopoli perdagangan yang semakin terancam oleh laluan perdagangan alternatif yang dikuasai kuasa Eropah.

                  Kejatuhan Melaka memberi kesan besar kepada kedudukan Melaka sebagai pusat perdagangan dan penyebaran Islam di rantau ini.
                </p>
              </div>
            </TabsContent>
          </Tabs>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <Button
              onClick={() => onNavigate('essay-writing', { essayId })}
              variant="outline"
              className="flex-1"
            >
              Try Again
            </Button>
            <Button
              onClick={() => onNavigate('essay-practice')}
              variant="outline"
              className="flex-1"
            >
              Practice Similar Question
            </Button>
            <Button
              onClick={() => onNavigate('essay-practice')}
              className="flex-1 bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
            >
              Back to Essay Practice
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
