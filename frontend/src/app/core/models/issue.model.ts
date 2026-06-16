export enum IssueStatus {
  OPEN = 'Open',
  IN_PROGRESS = 'In Progress',
  CLOSED = 'Closed',
}

export interface Issue {
  id: number;
  title: string;
  description: string | null;
  status: IssueStatus;
  created_at: string;
}

export interface IssuePage {
  items: Issue[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreateIssueDto {
  title: string;
  description?: string;
  status?: IssueStatus;
}

export interface UpdateIssueDto {
  title?: string;
  description?: string;
  status?: IssueStatus;
}
